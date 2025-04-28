import re
import time
import logging
import asyncio
import traceback

from vtuber_collector import CollectionMethod

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("vtuber_tracker")


class VtuberTrackerControl:
    def __init__(self, db, collector, debug=False) -> None:
        self.db = db
        self.collector = collector
        self.debug = debug

        # Initialize Google API client
        self.youtube_api = None
        self.api_quota_exceeded = False  # Flag to track quota status

        if collector.api_key:
            try:
                self.youtube_api = build(
                    "youtube", "v3", developerKey=collector.api_key
                )
                log.info("Successfully initialized YouTube Data API v3 client")
            except Exception as e:
                log.error(f"Failed to initialize YouTube API client: {e}")
                self.api_quota_exceeded = True  # Assume quota issue if can't initialize

        # For limiting channel list during debug
        if debug:
            self.channel_list = self.db.get_channelurl_list()[-10:]
        else:
            self.channel_list = self.db.get_channelurl_list()

        self.readylive = set()
        self.overtimelive = set()
        self.current_method = CollectionMethod.API  # Start with API method
        self.mainloop = asyncio.new_event_loop()

        # Track API quota usage
        self.api_units_used_today = 0
        self.api_quota_reset_time = time.time() + 86400  # Reset after 24 hours
        self.max_api_units_per_day = 10000  # Default, can be overridden in config

        # Start tasks
        time.sleep(3)
        self.mainloop.create_task(self.start_getdata())
        self.mainloop.create_task(self.check_readylist())
        self.mainloop.create_task(self.update_channel_data())
        self.mainloop.create_task(self.analyze_videos())
        self.mainloop.run_forever()

    def update_channel_list(self):
        """Refresh the channel list from the database."""
        if self.debug:
            self.channel_list = self.db.get_channelurl_list()[-10:]
        else:
            self.channel_list = self.db.get_channelurl_list()

        # Log platform distribution
        youtube_count = sum(1 for url in self.channel_list if "youtube" in url)
        twitch_count = sum(1 for url in self.channel_list if "twitch" in url)
        other_count = len(self.channel_list) - youtube_count - twitch_count

        log.info(f"Channel list updated: {len(self.channel_list)} total channels")
        log.info(
            f"Platform distribution: YouTube: {youtube_count}, Twitch: {twitch_count}, Other: {other_count}"
        )

    async def start_getdata(self):
        """Main loop for checking live status."""
        while True:
            starttime = time.time()
            checklist = [
                channel
                for channel in self.channel_list
                if channel not in self.readylive
            ]

            log.info(
                f"Live status check started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(starttime))}"
            )

            if not checklist:
                log.info("No channels to check")
            else:
                log.info(f"Checking {len(checklist)} channels")
                await self.run(checklist)

            endtime = time.time()
            log.info(
                f"Live status check finished at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime))}"
            )

            alltime = endtime - starttime
            log.info(
                f"Live status check completed in {int(alltime / 60)}m {int(alltime % 60)}s"
            )
            log.info(
                f"Next check scheduled for {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime + 600))}"
            )

            await asyncio.sleep(600)  # Check every 10 minutes
            self.update_channel_list()

    async def run(self, checklist):
        """Check live status for a list of channels."""
        tasks = []
        for channel_url in checklist:
            # Determine channel ID or handle
            channel_id = None

            if "youtube.com/channel/" in channel_url:
                channel_id = channel_url.split("youtube.com/channel/")[1].split("/")[0]
            elif "youtube.com/@" in channel_url:
                # Handle URL, will be processed by check_live_status
                channel_id = channel_url
            elif "twitch.tv/" in channel_url:
                # Twitch URL, will be processed by check_live_status
                channel_id = channel_url
            else:
                log.warning(f"Unsupported channel URL format: {channel_url}")
                continue

            # Add small delay between tasks to avoid rate limiting
            await asyncio.sleep(0.2)
            tasks.append(
                asyncio.create_task(self.check_live_status(channel_id, channel_url))
            )

        if tasks:
            nolivelist = []
            results, _ = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

            for result in results:
                try:
                    result_data = result.result()
                    if result_data["status"] == "LIVE":
                        log.info(f"{result_data['channel']} is live")
                    elif result_data["status"] == "READY_TO_LIVE":
                        self.readylive.add(result_data["channel"])
                        log.info(f"{result_data['channel']} is scheduled to go live")
                        self.mainloop.create_task(self.wait_live(result_data))
                    elif result_data["status"] is None:
                        nolivelist.append(result_data["channel"])
                        continue
                    else:
                        log.error(f"Unexpected status for {result_data['channel']}")
                        continue

                    self.db.update_live(result_data["channel"], result_data)
                except Exception as e:
                    log.error(f"Error processing live status result: {e}")
                    traceback.print_exc()

            # Clean up channels not live or scheduled
            if nolivelist:
                log.info(f"Removing {len(nolivelist)} channels from live database")
                self.db.clean_nolive(nolivelist)

    async def check_live_status(self, channel_id_or_url, channel_url):
        """Check live status for a single channel using YouTube API directly."""
        # Check if we should reset API quota counter
        if time.time() > self.api_quota_reset_time:
            log.info("Resetting API quota usage counter")
            self.api_units_used_today = 0
            self.api_quota_reset_time = time.time() + 86400  # 24 hours
            self.api_quota_exceeded = False  # Reset quota exceeded flag

        # Determine platform
        platform = "youtube"  # Default
        if "twitch.tv" in channel_url:
            platform = "twitch"

        if platform == "twitch":
            # For Twitch, always use scraping through ytlv
            try:
                log.debug(f"Checking Twitch live status for {channel_url}")
                live_status = self.collector.get_twitch_status(channel_url)
                return live_status
            except Exception as e:
                log.error(f"Error checking Twitch live status for {channel_url}: {e}")
                return {
                    "status": None,
                    "channel": channel_url,
                    "platform": "twitch",
                    "timestamp": None,
                }

        # YouTube processing from here
        # Extract channel ID if needed
        if "youtube.com/channel/" in channel_url:
            channel_id = channel_url.split("youtube.com/channel/")[1].split("/")[0]
        elif "youtube.com/@" in channel_url:
            # It's a handle URL, we need to get the channel ID
            try:
                channel_id = self.collector._extract_channel_id(channel_url)
            except Exception as e:
                log.error(
                    f"Error extracting channel ID from handle URL {channel_url}: {e}"
                )
                channel_id = channel_id_or_url
        else:
            channel_id = channel_id_or_url

        # Decide whether to use API or scraping
        # Check both our local quota flag and collector's status
        collector_can_use_api = self.collector._should_use_api()
        should_use_api = (
            not self.api_quota_exceeded
            and self.api_units_used_today < self.max_api_units_per_day
            and self.youtube_api is not None
            and collector_can_use_api
        )

        if should_use_api:
            try:
                log.debug(f"Using YouTube API to check live status for {channel_id}")
                self.current_method = CollectionMethod.API

                # Check for live broadcasts - costs 100 quota units
                self.api_units_used_today += 100
                live_request = self.youtube_api.search().list(
                    part="snippet",
                    channelId=channel_id,
                    eventType="live",
                    type="video",
                    maxResults=1,
                )
                live_response = live_request.execute()

                if len(live_response.get("items", [])) > 0:
                    # Channel is currently live
                    live_video = live_response["items"][0]
                    return {
                        "status": "LIVE",
                        "channel": channel_url,
                        "video_id": live_video["id"]["videoId"],
                        "title": live_video["snippet"]["title"],
                        "thumbnail": live_video["snippet"]["thumbnails"]["high"]["url"],
                        "platform": "youtube",
                        "timestamp": time.time(),
                    }

                # Check for upcoming streams - costs another 100 quota units
                self.api_units_used_today += 100
                upcoming_request = self.youtube_api.search().list(
                    part="snippet",
                    channelId=channel_id,
                    eventType="upcoming",
                    type="video",
                    maxResults=1,
                )
                upcoming_response = upcoming_request.execute()

                if len(upcoming_response.get("items", [])) > 0:
                    upcoming_video = upcoming_response["items"][0]

                    # Get detailed info about the upcoming stream - costs 1 quota unit
                    self.api_units_used_today += 1
                    video_request = self.youtube_api.videos().list(
                        part="liveStreamingDetails", id=upcoming_video["id"]["videoId"]
                    )
                    video_response = video_request.execute()

                    if "items" in video_response and video_response["items"]:
                        scheduled_time = video_response["items"][0][
                            "liveStreamingDetails"
                        ]["scheduledStartTime"]
                        # Convert ISO 8601 format to timestamp
                        scheduled_timestamp = time.mktime(
                            time.strptime(
                                scheduled_time.replace("Z", "GMT"),
                                "%Y-%m-%dT%H:%M:%S%Z",
                            )
                        )

                        return {
                            "status": "READY_TO_LIVE",
                            "channel": channel_url,
                            "video_id": upcoming_video["id"]["videoId"],
                            "title": upcoming_video["snippet"]["title"],
                            "thumbnail": upcoming_video["snippet"]["thumbnails"][
                                "high"
                            ]["url"],
                            "platform": "youtube",
                            "timestamp": scheduled_timestamp,
                        }

                # Not live or scheduled
                return {
                    "status": None,
                    "channel": channel_url,
                    "platform": "youtube",
                    "timestamp": None,
                }

            except HttpError as e:
                if e.resp.status in [403, 429]:
                    # API quota exceeded, switch to scraping
                    log.warning(
                        f"YouTube API quota exceeded, switching to scraping method: {e}"
                    )
                    self.current_method = CollectionMethod.SCRAPE
                    self.api_quota_exceeded = True  # Set flag for entire system
                    self.collector.api_calls_today = (
                        self.collector.max_api_calls_per_day + 1
                    )  # Also update collector
                    return await self._check_live_status_via_scrape(
                        channel_id_or_url, channel_url
                    )
                else:
                    log.error(f"YouTube API error: {e}")
                    return await self._check_live_status_via_scrape(
                        channel_id_or_url, channel_url
                    )
            except Exception as e:
                log.error(
                    f"Error using YouTube API to check live status for {channel_id}: {e}"
                )
                return await self._check_live_status_via_scrape(
                    channel_id_or_url, channel_url
                )
        else:
            # Use scraping method
            if (
                self.api_quota_exceeded
                or self.api_units_used_today >= self.max_api_units_per_day
            ):
                log.debug(
                    f"Using scraping method due to API quota limits for {channel_url}"
                )
            return await self._check_live_status_via_scrape(
                channel_id_or_url, channel_url
            )

    async def _check_live_status_via_scrape(self, channel_id_or_url, channel_url):
        """Fallback to scraping method when API is unavailable or quota exceeded."""
        try:
            log.debug(
                f"Using pure scraping method to check live status for {channel_url}"
            )
            self.current_method = CollectionMethod.SCRAPE

            # Determine platform
            if "twitch.tv" in channel_url:
                # For Twitch, use the ytlv library directly without going through collector
                try:
                    # Normalize URL
                    if "twitch.tv/" not in channel_url:
                        url = f"https://www.twitch.tv/{channel_url}"
                    else:
                        url = channel_url

                    # Use ytlv directly to avoid potential API calls in collector
                    from ytlv import twitch as ytlv_twitch

                    twitch_data = ytlv_twitch(url)

                    # Convert to dictionary
                    live_dict = {
                        "status": "LIVE" if twitch_data.islive else None,
                        "channel": url,
                        "platform": "twitch",
                        "timestamp": time.time() if twitch_data.islive else None,
                    }

                    # Add additional fields if available
                    if twitch_data.title:
                        live_dict["title"] = twitch_data.title
                    if twitch_data.picture:
                        live_dict["thumbnail"] = twitch_data.picture
                    if twitch_data.avatar:
                        live_dict["avatar"] = twitch_data.avatar

                    return live_dict
                except Exception as e:
                    log.error(f"Error scraping Twitch status: {e}")
                    return {
                        "status": None,
                        "channel": channel_url,
                        "platform": "twitch",
                        "timestamp": None,
                    }
            else:
                # For YouTube, use the ytlv library directly
                try:
                    # Normalize URL
                    if channel_id_or_url.startswith("UC"):
                        # It's a channel ID
                        url = f"https://www.youtube.com/channel/{channel_id_or_url}"
                    elif "youtube.com/channel/" in channel_id_or_url:
                        # It's already a channel URL
                        url = channel_id_or_url
                    elif "@" in channel_id_or_url:
                        # It's a handle or handle URL
                        if "youtube.com" in channel_id_or_url:
                            url = channel_id_or_url
                        else:
                            # Just the handle
                            url = f"https://www.youtube.com/{channel_id_or_url}"
                    else:
                        # Unknown format, try as is
                        url = channel_id_or_url

                    # Use ytlv directly to avoid potential API calls in collector
                    from ytlv import youtube as ytlv_youtube

                    live_data = ytlv_youtube(url)

                    # Convert to dictionary
                    live_dict = {
                        "status": live_data.status,
                        "channel": url,
                        "platform": "youtube",
                        "timestamp": live_data.timestamp,
                    }

                    # Add additional fields if available
                    if hasattr(live_data, "title") and live_data.title:
                        live_dict["title"] = live_data.title
                    if hasattr(live_data, "picture") and live_data.picture:
                        live_dict["thumbnail"] = live_data.picture
                    if hasattr(live_data, "link") and live_data.link:
                        # Extract video ID from the URL if possible
                        if live_data.link and "youtube.com/watch?v=" in live_data.link:
                            video_id = live_data.link.split("v=")[1].split("&")[0]
                            live_dict["video_id"] = video_id

                    return live_dict
                except Exception as e:
                    log.error(f"Error with pure scraping for YouTube: {e}")
                    return {
                        "status": None,
                        "channel": channel_url,
                        "platform": "youtube",
                        "timestamp": None,
                    }
        except Exception as e:
            log.error(f"Error checking live status via scraping for {channel_url}: {e}")
            return {
                "status": None,
                "channel": channel_url,
                "platform": "youtube" if "twitch.tv" not in channel_url else "twitch",
                "timestamp": None,
            }

    async def wait_live(self, result):
        """Wait for a scheduled stream to go live."""
        if not result["timestamp"]:
            log.warning(f"No timestamp for scheduled stream: {result['channel']}")
            self.readylive.remove(result["channel"])
            return

        wait_time = int(result["timestamp"] - time.time())
        if wait_time <= 0:
            log.warning(f"Stream already past scheduled time: {result['channel']}")
            wait_time = 60  # Check after 1 minute

        log.info(f"Waiting {wait_time} seconds for {result['channel']} to go live")
        await asyncio.sleep(wait_time)

        # Determine platform and channel ID
        platform = result.get("platform", "youtube")
        channel_url = result["channel"]

        # Extract channel ID based on platform
        channel_id = None
        if platform == "youtube":
            if "youtube.com/channel/" in channel_url:
                channel_id = channel_url.split("youtube.com/channel/")[1].split("/")[0]
            elif "youtube.com/@" in channel_url:
                # It's a handle URL
                channel_id = channel_url
            else:
                # Try to extract based on pattern
                channel_id_match = re.search(r"youtube\.com/([^/]+)", channel_url)
                if channel_id_match:
                    channel_id = channel_id_match.group(1)
                else:
                    channel_id = channel_url
        else:  # twitch
            channel_id = channel_url  # We'll use the full URL

        if not channel_id:
            log.error(f"Could not extract channel ID from {result['channel']}")
            self.readylive.remove(result["channel"])
            return

        # Check if now live
        res = await self.check_live_status(channel_id, result["channel"])

        if res["status"] == "LIVE":
            log.info(f"{res['channel']} is now live")
            self.readylive.remove(result["channel"])
            self.db.update_live(result["channel"], res)
        else:
            log.info(
                f"{res['channel']} is not live yet, will retry every minute for 10 minutes"
            )

            # Retry for 10 minutes
            for i in range(10):
                res = await self.check_live_status(channel_id, result["channel"])

                if res["status"] == "LIVE":
                    log.info(f"{res['channel']} is now live after retry {i + 1}")
                    self.readylive.remove(result["channel"])
                    self.db.update_live(result["channel"], res)
                    return

                await asyncio.sleep(60)

            log.info(
                f"{res['channel']} did not go live within retry window, removing from ready list"
            )
            self.readylive.remove(result["channel"])
            self.db.update_live(result["channel"], res)

    async def check_readylist(self):
        """Periodically check the ready list for stale entries."""
        while True:
            log.info("Checking ready list for stale entries")
            cplist = self.readylive.copy()

            for channel_url in cplist:
                # Extract channel ID from URL
                channel_id = None
                if "youtube.com/channel/" in channel_url:
                    channel_id = channel_url.split("youtube.com/channel/")[1].split(
                        "/"
                    )[0]

                if not channel_id:
                    log.warning(
                        f"Could not extract channel ID from {channel_url}, removing from ready list"
                    )
                    self.readylive.remove(channel_url)
                    continue

                # Check status
                res = await self.check_live_status(channel_id, channel_url)

                if res["status"] is None:
                    self.readylive.remove(channel_url)
                    log.warning(
                        f"{channel_url} is no longer scheduled, removing from ready list"
                    )

            # Check again in 30 minutes
            await asyncio.sleep(1800)

    async def update_channel_data(self):
        """Periodically update channel information using YouTube API directly."""
        while True:
            log.info("Starting channel data update")
            start_time = time.time()

            # Get all channel URLs
            channel_urls = self.db.get_channelurl_list()

            # Process in smaller batches to avoid overwhelming the API
            batch_size = 20
            for i in range(0, len(channel_urls), batch_size):
                batch = channel_urls[i : i + batch_size]
                log.info(
                    f"Processing batch {i // batch_size + 1}/{(len(channel_urls) + batch_size - 1) // batch_size}"
                )

                channel_ids = []
                url_to_id_map = {}

                #TODO: 新增 對 @channel_url 的處理
                for channel_url in batch:
                    if "youtube.com/channel/" in channel_url:
                        channel_id = channel_url.split("youtube.com/channel/")[1].split(
                            "/"
                        )[0]
                        channel_ids.append(channel_id)
                        url_to_id_map[channel_id] = channel_url
                    else:
                        log.warning(f"Unsupported channel URL format: {channel_url}")

                # Check if we should use API
                should_use_api = (
                    self.api_units_used_today < self.max_api_units_per_day
                ) and self.youtube_api is not None

                if should_use_api and channel_ids:
                    try:
                        log.info(
                            f"Using YouTube API to update data for {len(channel_ids)} channels"
                        )
                        self.current_method = CollectionMethod.API

                        # Process channels in batches of 50 (API limit)
                        for j in range(0, len(channel_ids), 50):
                            chunk = channel_ids[j : j + 50]

                            # Get channel data - costs 1 quota unit per channel
                            self.api_units_used_today += len(chunk)
                            channel_request = self.youtube_api.channels().list(
                                part="snippet,statistics,contentDetails,brandingSettings",
                                id=",".join(chunk),
                            )
                            channel_response = channel_request.execute()

                            for channel in channel_response.get("items", []):
                                channel_id = channel["id"]

                                # Extract company/organization (heuristic)
                                company = "Independent"
                                description = channel["snippet"]["description"].lower()
                                if "hololive" in description:
                                    company = "Hololive"
                                elif (
                                    "にじさんじ" in description
                                    or "nijisanji" in description
                                ):
                                    company = "Nijisanji"
                                elif "vshojo" in description:
                                    company = "VShojo"
                                elif "phase connect" in description:
                                    company = "Phase Connect"

                                # Build channel data for database
                                channel_data = {
                                    "channel_id": channel_id,
                                    "name": channel["snippet"]["title"],
                                    "description": channel["snippet"]["description"],
                                    "custom_url": channel["snippet"].get(
                                        "customUrl", ""
                                    ),
                                    "published_at": channel["snippet"]["publishedAt"],
                                    "thumbnail": channel["snippet"]["thumbnails"][
                                        "high"
                                    ]["url"],
                                    "country": channel["snippet"].get("country", ""),
                                    "view_count": int(
                                        channel["statistics"]["viewCount"]
                                    ),
                                    "subscriber_count": int(
                                        channel["statistics"].get("subscriberCount", 0)
                                    ),
                                    "hidden_subscriber_count": channel[
                                        "statistics"
                                    ].get("hiddenSubscriberCount", False),
                                    "video_count": int(
                                        channel["statistics"]["videoCount"]
                                    ),
                                    "company": company,
                                    "activity_status": "active",  # Default
                                    "debut_date": channel["snippet"][
                                        "publishedAt"
                                    ],  # Approximation
                                    "platform": "youtube",
                                    "channel_url": url_to_id_map.get(
                                        channel_id,
                                        f"https://www.youtube.com/channel/{channel_id}",
                                    ),
                                    "last_updated": time.time(),
                                }

                                # Update database
                                self.db.insert_channel(channel_data)
                                log.info(
                                    f"Updated data for {channel_data['name']} ({channel_id})"
                                )

                            # Add delay between API requests
                            await asyncio.sleep(1)

                    except HttpError as e:
                        if e.resp.status in [403, 429]:
                            # API quota exceeded, switch to scraping
                            log.warning(
                                f"YouTube API quota exceeded, switching to scraping method: {e}"
                            )
                            self.current_method = CollectionMethod.SCRAPE
                            await self._update_channel_data_via_scrape(batch)
                        else:
                            log.error(f"YouTube API error: {e}")
                            await self._update_channel_data_via_scrape(batch)
                    except Exception as e:
                        log.error(
                            f"Error using YouTube API to update channel data: {e}"
                        )
                        await self._update_channel_data_via_scrape(batch)
                else:
                    # Use scraping method
                    await self._update_channel_data_via_scrape(batch)

                # Add delay between batches
                await asyncio.sleep(10)

            end_time = time.time()
            elapsed = end_time - start_time

            log.info(f"Channel data update completed in {elapsed:.2f} seconds")

            # Update once per day
            await asyncio.sleep(86400)

    async def _update_channel_data_via_scrape(self, channel_urls):
        """Fallback to collector method when API is unavailable or quota exceeded."""
        log.info(
            f"Using scraping method to update data for {len(channel_urls)} channels"
        )
        self.current_method = CollectionMethod.SCRAPE

        for channel_url in channel_urls:
            try:
                # Extract channel ID
                #TODO: 新增 對 @channel_url 的處理
                if "youtube.com/channel/" in channel_url:
                    channel_id = channel_url.split("youtube.com/channel/")[1].split(
                        "/"
                    )[0]

                    # Get channel data using collector
                    channel_data = self.collector.get_channel_info(channel_id)

                    # Update database
                    self.db.insert_channel(channel_data)

                    log.info(
                        f"Updated data for {channel_data['name']} ({channel_id}) via scraping"
                    )
                else:
                    log.warning(f"Unsupported channel URL format: {channel_url}")

                # Add delay to avoid rate limits
                await asyncio.sleep(1)
            except Exception as e:
                log.error(
                    f"Error updating channel data via scraping for {channel_url}: {e}"
                )

        return True

    async def analyze_videos(self):
        """Analyze videos for all channels using YouTube API directly."""
        while True:
            log.info("Starting video analysis")
            start_time = time.time()

            # Get all channel URLs
            channel_urls = self.db.get_channelurl_list()

            # Process in smaller batches
            batch_size = 20
            for i in range(0, len(channel_urls), batch_size):
                batch = channel_urls[i : i + batch_size]
                log.info(
                    f"Processing batch {i // batch_size + 1}/{(len(channel_urls) + batch_size - 1) // batch_size}"
                )

                for channel_url in batch:
                    try:
                        # Extract channel ID
                        #TODO: 新增 對 @channel_url 的處理
                        if "youtube.com/channel/" in channel_url:
                            channel_id = channel_url.split("youtube.com/channel/")[
                                1
                            ].split("/")[0]

                            # Check if we should use API
                            should_use_api = (
                                self.api_units_used_today < self.max_api_units_per_day
                            ) and self.youtube_api is not None

                            if should_use_api:
                                await self._analyze_videos_via_api(channel_id)
                            else:
                                await self._analyze_videos_via_scrape(channel_id)
                        else:
                            log.warning(
                                f"Unsupported channel URL format: {channel_url}"
                            )

                        # Add delay between channels
                        await asyncio.sleep(2)
                    except Exception as e:
                        log.error(f"Error analyzing videos for {channel_url}: {e}")

                # Add delay between batches
                await asyncio.sleep(10)

            end_time = time.time()
            elapsed = end_time - start_time

            log.info(f"Video analysis completed in {elapsed:.2f} seconds")

            # Update every 6 hours
            await asyncio.sleep(21600)

    async def _analyze_videos_via_api(self, channel_id):
        """Analyze videos using the YouTube API directly."""
        try:
            log.info(f"Using YouTube API to analyze videos for channel {channel_id}")
            self.current_method = CollectionMethod.API

            # Get recent videos - costs 100 quota units
            self.api_units_used_today += 100
            search_request = self.youtube_api.search().list(
                part="snippet,id",
                channelId=channel_id,
                maxResults=10,
                order="date",
                type="video",
            )
            search_response = search_request.execute()

            video_ids = []
            for item in search_response.get("items", []):
                if item["id"]["kind"] == "youtube#video":
                    video_ids.append(item["id"]["videoId"])

            if not video_ids:
                log.info(f"No videos found for channel {channel_id}")
                return

            # Get detailed video information in batch - costs 1 quota unit per video
            self.api_units_used_today += len(video_ids)
            video_request = self.youtube_api.videos().list(
                part="snippet,statistics,contentDetails,liveStreamingDetails",
                id=",".join(video_ids),
            )
            video_response = video_request.execute()

            for video in video_response.get("items", []):
                video_id = video["id"]

                # Check if we already have detailed info for this video
                existing_video = self.db.get_video(video_id)
                if existing_video and "view_count" in existing_video:
                    log.debug(f"Video {video_id} already analyzed, skipping")
                    continue

                # Detect collaborations from description
                collaborators = self._detect_collaborations(
                    video["snippet"]["description"]
                )

                # Build video data
                video_data = {
                    "video_id": video_id,
                    "title": video["snippet"]["title"],
                    "description": video["snippet"]["description"],
                    "published_at": video["snippet"]["publishedAt"],
                    "channel_id": video["snippet"]["channelId"],
                    "channel_title": video["snippet"]["channelTitle"],
                    "tags": video["snippet"].get("tags", []),
                    "category_id": video["snippet"]["categoryId"],
                    "thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                    "duration": video["contentDetails"]["duration"],
                    "view_count": int(video["statistics"].get("viewCount", 0)),
                    "like_count": int(video["statistics"].get("likeCount", 0)),
                    "comment_count": int(video["statistics"].get("commentCount", 0)),
                    "collaborators": collaborators,
                }

                # Add live streaming details if available
                if "liveStreamingDetails" in video:
                    video_data.update(
                        {
                            "actual_start_time": video["liveStreamingDetails"].get(
                                "actualStartTime"
                            ),
                            "actual_end_time": video["liveStreamingDetails"].get(
                                "actualEndTime"
                            ),
                            "scheduled_start_time": video["liveStreamingDetails"].get(
                                "scheduledStartTime"
                            ),
                            "concurrent_viewers": video["liveStreamingDetails"].get(
                                "concurrentViewers"
                            ),
                        }
                    )

                # Store in database
                self.db.insert_video(video_data)
                log.info(f"Analyzed video: {video_data['title']} ({video_id})")

                # Add delay to avoid rate limits
                await asyncio.sleep(0.5)

        except HttpError as e:
            if e.resp.status in [403, 429]:
                # API quota exceeded, switch to scraping
                log.warning(
                    f"YouTube API quota exceeded, switching to scraping method: {e}"
                )
                self.current_method = CollectionMethod.SCRAPE
                await self._analyze_videos_via_scrape(channel_id)
            else:
                log.error(f"YouTube API error: {e}")
                await self._analyze_videos_via_scrape(channel_id)
        except Exception as e:
            log.error(
                f"Error using YouTube API to analyze videos for {channel_id}: {e}"
            )
            await self._analyze_videos_via_scrape(channel_id)

    async def _analyze_videos_via_scrape(self, channel_id):
        """Fallback to collector method when API is unavailable or quota exceeded."""
        try:
            log.info(
                f"Using scraping method to analyze videos for channel {channel_id}"
            )
            self.current_method = CollectionMethod.SCRAPE

            # Get recent videos (limit to 10)
            videos_data = self.collector.get_videos(channel_id, max_results=10)

            for video in videos_data.get("videos", []):
                # Check if we already have detailed info for this video
                existing_video = self.db.get_video(video["video_id"])
                if existing_video and "view_count" in existing_video:
                    continue

                # Get detailed video information
                video_details = self.collector.get_video_details(video["video_id"])

                # Store in database
                self.db.insert_video(video_details)

                log.info(
                    f"Analyzed video via scraping: {video_details['title']} ({video['video_id']})"
                )

                # Add delay to avoid rate limits
                await asyncio.sleep(1)

        except Exception as e:
            log.error(f"Error analyzing videos via scraping for {channel_id}: {e}")

    def _detect_collaborations(self, description):
        """Detect collaborations mentioned in the video description."""
        collaborators = []

        # Pattern: YouTube channel links
        youtube_patterns = [
            r"(?:https?://)?(?:www\.)?youtube\.com/(?:channel/|c/|@)([^\s/]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/user/([^\s/]+)",
        ]

        for pattern in youtube_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                collaborators.append({"channel_id": match, "platform": "youtube"})

        # Pattern: Common collaboration keywords in different languages
        collab_patterns = [
            r"(?:collab|collaboration|コラボ|合作).*?(?:with|w/|と|with\s+@([^\s]+))",
            r"(?:ft\.|featuring|出演者).*?(?:@([^\s]+))",
        ]

        for pattern in collab_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                if match and not any(c["channel_id"] == match for c in collaborators):
                    collaborators.append(
                        {
                            "channel_id": match,
                            "platform": "mention",  # Needs further verification
                        }
                    )

        return collaborators
