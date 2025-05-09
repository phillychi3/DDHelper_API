import json
import logging
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from ytlv import twitch as ytlv_twitch
from ytlv import youtube as ytlv_youtube

logger = logging.getLogger("VtuberCollector")


class CollectionMethod(Enum):
    API = "api"
    SCRAPE = "scrape"


class VtuberCollector:
    """
    VtuberCollector handles data collection from different platforms (YouTube, Twitch).
    It supports both API and scraping methods, with automatic fallback to scraping when API limits are reached.
    """

    def __init__(self, api_key: str, max_api_calls_per_day: int = 10000):
        """
        Initialize the collector with API key and limits.

        Args:
            api_key: YouTube API key
            max_api_calls_per_day: Maximum API calls allowed per day
        """
        self.api_key = api_key
        self.max_api_calls_per_day = max_api_calls_per_day
        self.api_calls_today = 0
        self.api_call_reset_time = time.time() + 86400  # 24 hours from now
        self.current_method = CollectionMethod.API

    def _should_use_api(self) -> bool:
        """Determine if we should use the API or fall back to scraping."""
        if time.time() > self.api_call_reset_time:
            self.api_calls_today = 0
            self.api_call_reset_time = time.time() + 86400

        return self.api_calls_today < self.max_api_calls_per_day and self.api_key

    def _get_via_api(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data using the YouTube API.

        Args:
            endpoint: API endpoint (e.g., "channels", "videos")
            params: API parameters

        Returns:
            API response as dictionary
        """
        params["key"] = self.api_key
        response = requests.get(
            f"https://www.googleapis.com/youtube/v3/{endpoint}", params=params
        )
        self.api_calls_today += 1

        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")

        return response.json()

    def _extract_channel_id(self, channel_url_or_id: str) -> str:
        """
        Extract YouTube channel ID from various URL formats or handle.

        Supports:
        - Channel URLs: https://www.youtube.com/channel/UCdn5BQ06XqgXoAxIhbqw5Rg
        - Channel IDs: UCdn5BQ06XqgXoAxIhbqw5Rg
        - Handle URLs: https://www.youtube.com/@ShirakamiFubuki
        - Handle names: @ShirakamiFubuki

        Returns:
            Channel ID or original input if can't extract
        """
        # If it's already a channel ID (starts with UC and is 24 chars)
        if re.match(r"^UC[A-Za-z0-9_-]{22}$", channel_url_or_id):
            return channel_url_or_id

        # Extract from channel URL
        channel_id_match = re.search(
            r"youtube\.com/channel/([^/?&]+)", channel_url_or_id
        )
        if channel_id_match:
            return channel_id_match.group(1)

        # For handle URLs and names, we need to make a request to get the channel ID
        if "@" in channel_url_or_id:
            handle = channel_url_or_id
            if not handle.startswith("@"):
                # Extract handle from URL
                handle_match = re.search(r"youtube\.com/@([^/?&]+)", channel_url_or_id)
                if handle_match:
                    handle = "@" + handle_match.group(1)
                else:
                    logger.error(f"Could not extract handle from {channel_url_or_id}")
                    return channel_url_or_id  # Return as is, will be handled later

            # Now we have the handle, get the channel ID
            try:
                if self._should_use_api():
                    # Using API to get channel ID from handle
                    params = {
                        "key": self.api_key,
                        "forHandle": handle.lstrip("@"),
                        "part": "id",
                    }
                    response = requests.get(
                        "https://www.googleapis.com/youtube/v3/channels", params=params
                    )
                    self.api_calls_today += 1

                    data = response.json()
                    if "items" in data and data["items"]:
                        return data["items"][0]["id"]

                # Fallback to scraping
                handle_url = f"https://www.youtube.com/{handle}"
                response = requests.get(handle_url)

                # Try to extract channel ID from the page
                channel_id_patterns = [
                    r'"channelId":"(UC[A-Za-z0-9_-]{22})"',
                    r'"externalChannelId":"(UC[A-Za-z0-9_-]{22})"',
                    r"channelId\\x22:\\x22(UC[A-Za-z0-9_-]{22})\\x22",
                ]

                for pattern in channel_id_patterns:
                    matches = re.search(pattern, response.text)
                    if matches:
                        return matches.group(1)

                logger.error(f"Could not extract channel ID from handle {handle}")
                return channel_url_or_id  # Return as is, will be handled later

            except Exception as e:
                logger.error(f"Error getting channel ID from handle {handle}: {e}")
                return channel_url_or_id  # Return as is, will be handled later

        # If we can't determine the channel ID, return the original string
        return channel_url_or_id

    def _extract_company(self, channel_data: Dict[str, Any]) -> str:
        """
        Try to extract the company from channel data.

        Args:
            channel_data: Channel data from API

        Returns:
            Company name or "Independent"
        """
        # This is a heuristic and not always accurate
        description = channel_data["snippet"]["description"].lower()

        company_keywords = {
            "hololive": "Hololive",
            "にじさんじ": "Nijisanji",
            "nijisanji": "Nijisanji",
            "vshojo": "VShojo",
            "phase connect": "Phase Connect",
            "vspo": "VSpo",
            "774inc": "774inc",
            "voms": "VOMS",
        }

        for keyword, company in company_keywords.items():
            if keyword in description:
                return company

        return "Independent"

    def _parse_count(self, count_text: str) -> int:
        """
        Parse count text from YouTube (e.g., '1.2M subscribers').

        Args:
            count_text: Text representation of count

        Returns:
            Integer value
        """
        try:
            # Remove non-numeric characters except '.' and 'K', 'M', 'B'
            count_text = "".join(
                c for c in count_text if c.isdigit() or c in [".", "K", "M", "B"]
            )

            multiplier = 1
            if "K" in count_text:
                multiplier = 1000
                count_text = count_text.replace("K", "")
            elif "M" in count_text:
                multiplier = 1000000
                count_text = count_text.replace("M", "")
            elif "B" in count_text:
                multiplier = 1000000000
                count_text = count_text.replace("B", "")

            return int(float(count_text) * multiplier)
        except:
            return 0

    # ============ YouTube Methods ============

    def get_channel_info(self, channel_url_or_id: str) -> Dict[str, Any]:
        """
        Get information about a YouTube channel.

        Args:
            channel_url_or_id: YouTube channel ID, URL, or handle

        Returns:
            Dictionary with channel information
        """
        # Extract channel ID from URL or handle
        channel_id = self._extract_channel_id(channel_url_or_id)

        if self._should_use_api():
            self.current_method = CollectionMethod.API
            data = self._get_via_api(
                "channels",
                {
                    "part": "snippet,statistics,contentDetails,brandingSettings",
                    "id": channel_id,
                },
            )

            if "items" not in data or not data["items"]:
                logger.error(f"Failed to get channel info for {channel_id} via API")
                self.current_method = CollectionMethod.SCRAPE
                return self._get_channel_info_via_scrape(channel_id)

            channel = data["items"][0]

            return {
                "channel_id": channel_id,
                "name": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "custom_url": channel["snippet"].get("customUrl", ""),
                "published_at": channel["snippet"]["publishedAt"],
                "thumbnail": channel["snippet"]["thumbnails"]["high"]["url"],
                "country": channel["snippet"].get("country", ""),
                "view_count": int(channel["statistics"]["viewCount"]),
                "subscriber_count": int(
                    channel["statistics"].get("subscriberCount", 0)
                ),
                "hidden_subscriber_count": channel["statistics"].get(
                    "hiddenSubscriberCount", False
                ),
                "video_count": int(channel["statistics"]["videoCount"]),
                "company": self._extract_company(channel),
                "activity_status": "active",  # Default, can be updated manually
                "debut_date": channel["snippet"][
                    "publishedAt"
                ],  # Usually not exact, can be updated manually
                "platform": "youtube",
                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                "handle": channel["snippet"].get("customUrl", "").replace("@", "")
                if channel["snippet"].get("customUrl")
                else "",
                "last_updated": time.time(),
            }
        else:
            self.current_method = CollectionMethod.SCRAPE
            return self._get_channel_info_via_scrape(channel_id)

    def _get_channel_info_via_scrape(self, channel_id: str) -> Dict[str, Any]:
        """
        Get channel info using web scraping as a fallback.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dictionary with channel information
        """
        try:
            url = f"https://www.youtube.com/channel/{channel_id}"
            response = requests.get(url)

            # Extract subscriber count
            subscriber_pattern = r'"subscriberCountText":\{"simpleText":"(.*?)"'
            subscriber_match = re.search(subscriber_pattern, response.text)
            subscriber_text = subscriber_match.group(1) if subscriber_match else "0"
            subscriber_count = self._parse_count(subscriber_text)

            # Extract view count
            view_pattern = r'"viewCountText":\{"simpleText":"(.*?)"'
            view_match = re.search(view_pattern, response.text)
            view_text = view_match.group(1) if view_match else "0"
            view_count = self._parse_count(view_text)

            # Extract channel name
            title_pattern = r'<meta name="title" content="(.*?)">'
            title_match = re.search(title_pattern, response.text)
            channel_name = title_match.group(1) if title_match else "Unknown Channel"

            # Extract description
            description_pattern = r'"description":\{"simpleText":"(.*?)"\}'
            description_match = re.search(description_pattern, response.text)
            description = description_match.group(1) if description_match else ""

            # Extract thumbnail
            thumbnail_pattern = r'"avatar":\{"thumbnails":\[\{"url":"(.*?)"'
            thumbnail_match = re.search(thumbnail_pattern, response.text)
            thumbnail = thumbnail_match.group(1) if thumbnail_match else ""

            # Try to extract handle
            handle_pattern = r'"canonicalChannelUrl":"https://www.youtube.com/@([^"]+)"'
            handle_match = re.search(handle_pattern, response.text)
            handle = handle_match.group(1) if handle_match else ""

            return {
                "channel_id": channel_id,
                "name": channel_name,
                "description": description,
                "custom_url": f"@{handle}" if handle else "",
                "published_at": "",  # Can't reliably get this from scraping
                "thumbnail": thumbnail,
                "country": "",  # Can't reliably get this from scraping
                "view_count": view_count,
                "subscriber_count": subscriber_count,
                "hidden_subscriber_count": subscriber_count == 0,
                "video_count": 0,  # Can't reliably get this from scraping
                "company": "Unknown",  # Need manual categorization
                "activity_status": "active",
                "debut_date": "",  # Can't reliably get this from scraping
                "platform": "youtube",
                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                "handle": handle,
                "last_updated": time.time(),
            }
        except Exception as e:
            logger.error(f"Error scraping channel {channel_id}: {e}")
            return {
                "channel_id": channel_id,
                "name": "Unknown Channel",
                "platform": "youtube",
                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                "last_updated": time.time(),
            }

    def get_live_status(self, channel_url_or_id: str) -> Dict[str, Any]:
        """
        Check if a YouTube channel is currently live or has upcoming streams.

        Args:
            channel_url_or_id: YouTube channel ID, URL, or handle

        Returns:
            Dictionary with live status information
        """
        # Extract channel ID from URL or handle
        channel_id = self._extract_channel_id(channel_url_or_id)
        channel_url = f"https://www.youtube.com/channel/{channel_id}"

        if self._should_use_api():
            self.current_method = CollectionMethod.API
            # Check for live streams
            data = self._get_via_api(
                "search",
                {
                    "part": "snippet",
                    "channelId": channel_id,
                    "eventType": "live",
                    "type": "video",
                    "maxResults": 1,
                },
            )

            if len(data.get("items", [])) > 0:
                # Channel is currently live
                live_video = data["items"][0]
                return {
                    "status": "LIVE",
                    "channel": channel_url,
                    "video_id": live_video["id"]["videoId"],
                    "title": live_video["snippet"]["title"],
                    "thumbnail": live_video["snippet"]["thumbnails"]["high"]["url"],
                    "platform": "youtube",
                    "timestamp": time.time(),
                }

            # Check for upcoming streams
            upcoming_data = self._get_via_api(
                "search",
                {
                    "part": "snippet",
                    "channelId": channel_id,
                    "eventType": "upcoming",
                    "type": "video",
                    "maxResults": 1,
                },
            )

            if len(upcoming_data.get("items", [])) > 0:
                upcoming_video = upcoming_data["items"][0]
                video_details = self._get_via_api(
                    "videos",
                    {
                        "part": "liveStreamingDetails",
                        "id": upcoming_video["id"]["videoId"],
                    },
                )

                if "items" in video_details and video_details["items"]:
                    scheduled_time = video_details["items"][0]["liveStreamingDetails"][
                        "scheduledStartTime"
                    ]
                    timestamp = time.mktime(
                        time.strptime(scheduled_time, "%Y-%m-%dT%H:%M:%SZ")
                    )

                    return {
                        "status": "READY_TO_LIVE",
                        "channel": channel_url,
                        "video_id": upcoming_video["id"]["videoId"],
                        "title": upcoming_video["snippet"]["title"],
                        "thumbnail": upcoming_video["snippet"]["thumbnails"]["high"][
                            "url"
                        ],
                        "platform": "youtube",
                        "timestamp": timestamp,
                    }

            return {
                "status": None,
                "channel": channel_url,
                "platform": "youtube",
                "timestamp": None,
            }
        else:
            self.current_method = CollectionMethod.SCRAPE
            return self._get_live_status_via_scrape(channel_url_or_id)

    def _get_live_status_via_scrape(self, channel_url_or_id: str) -> Dict[str, Any]:
        """
        Get live status using ytlv library as a fallback.

        Args:
            channel_url_or_id: YouTube channel ID, URL, or handle

        Returns:
            Dictionary with live status information
        """
        try:
            # Determine URL type and extract channel URL
            if channel_url_or_id.startswith("UC"):
                # It's a channel ID
                channel_url = f"https://www.youtube.com/channel/{channel_url_or_id}"
            elif "youtube.com/channel/" in channel_url_or_id:
                # It's already a channel URL
                channel_url = channel_url_or_id
            elif "@" in channel_url_or_id:
                # It's a handle or handle URL
                if "youtube.com" in channel_url_or_id:
                    channel_url = channel_url_or_id
                else:
                    # Just the handle
                    channel_url = f"https://www.youtube.com/{channel_url_or_id}"
            else:
                # Unknown format, try as is
                channel_url = channel_url_or_id

            # Use ytlv to get live status
            live_data = ytlv_youtube(channel_url)

            # Convert to dictionary
            live_dict = {
                "status": live_data.status,
                "channel": channel_url,
                "platform": "youtube",
                "timestamp": live_data.timestamp,
            }

            # Add additional fields if available
            if hasattr(live_data, "title") and live_data.title:
                live_dict["title"] = live_data.title
            if hasattr(live_data, "picture") and live_data.picture:
                live_dict["thumbnail"] = live_data.picture
            if hasattr(live_data, "link") and live_data.link:
                # Extract video ID from the URL
                video_id_match = re.search(r"v=([^&]+)", live_data.link)
                if video_id_match:
                    live_dict["video_id"] = video_id_match.group(1)

            return live_dict
        except Exception as e:
            logger.error(
                f"Error getting live status for {channel_url_or_id} via scrape: {e}"
            )
            # Try to extract channel ID for the error response
            try:
                channel_id = self._extract_channel_id(channel_url_or_id)
                channel_url = f"https://www.youtube.com/channel/{channel_id}"
            except:
                channel_url = channel_url_or_id

            return {
                "status": None,
                "channel": channel_url,
                "platform": "youtube",
                "timestamp": None,
            }

    def get_videos(
        self, channel_url_or_id: str, max_results: int = 50, page_token: str = ""
    ) -> Dict[str, Any]:
        """
        Get a list of videos from a YouTube channel.

        Args:
            channel_url_or_id: YouTube channel ID, URL, or handle
            max_results: Maximum number of results to return
            page_token: Token for pagination

        Returns:
            Dictionary with videos information
        """
        # Extract channel ID from URL or handle
        channel_id = self._extract_channel_id(channel_url_or_id)

        if self._should_use_api():
            self.current_method = CollectionMethod.API
            data = self._get_via_api(
                "search",
                {
                    "part": "snippet,id",
                    "channelId": channel_id,
                    "maxResults": max_results,
                    "order": "date",
                    "pageToken": page_token,
                    "type": "video",
                },
            )

            videos = []
            for item in data.get("items", []):
                if item["id"]["kind"] == "youtube#video":
                    videos.append(
                        {
                            "video_id": item["id"]["videoId"],
                            "title": item["snippet"]["title"],
                            "description": item["snippet"]["description"],
                            "published_at": item["snippet"]["publishedAt"],
                            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        }
                    )

            return {
                "videos": videos,
                "next_page_token": data.get("nextPageToken", ""),
                "total_results": data.get("pageInfo", {}).get("totalResults", 0),
            }
        else:
            self.current_method = CollectionMethod.SCRAPE
            return self._get_videos_via_scrape(channel_id, max_results)

    def _get_videos_via_scrape(
        self, channel_id: str, max_results: int
    ) -> Dict[str, Any]:
        """
        Get videos using web scraping as a fallback.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results to return

        Returns:
            Dictionary with videos information
        """
        try:
            url = f"https://www.youtube.com/channel/{channel_id}/videos"
            response = requests.get(url)

            videos = []
            video_pattern = r'"videoRenderer":{"videoId":"(.*?)","thumbnail":.*?"title":{"runs":\[{"text":"(.*?)"}]'
            video_matches = re.finditer(video_pattern, response.text)

            count = 0
            for match in video_matches:
                if count >= max_results:
                    break

                video_id = match.group(1)
                title = match.group(2)

                videos.append(
                    {
                        "video_id": video_id,
                        "title": title,
                        "description": "",  # Can't easily get from this page
                        "published_at": "",  # Can't easily get from this page
                        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    }
                )
                count += 1

            return {
                "videos": videos,
                "next_page_token": "",
                "total_results": len(videos),
            }
        except Exception as e:
            logger.error(f"Error scraping videos for {channel_id}: {e}")
            return {"videos": [], "next_page_token": "", "total_results": 0}

    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a YouTube video.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video details
        """
        if self._should_use_api():
            self.current_method = CollectionMethod.API
            data = self._get_via_api(
                "videos",
                {
                    "part": "snippet,statistics,contentDetails,liveStreamingDetails",
                    "id": video_id,
                },
            )

            if "items" not in data or not data["items"]:
                logger.error(f"Failed to get video details for {video_id} via API")
                self.current_method = CollectionMethod.SCRAPE
                return self._get_video_details_via_scrape(video_id)

            video = data["items"][0]
            details = {
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
            }

            # Add live streaming details if available
            if "liveStreamingDetails" in video:
                details.update(
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

            # Detect collaborations
            details["collaborators"] = self.detect_collaborators(
                video["snippet"]["description"]
            )

            return details
        else:
            self.current_method = CollectionMethod.SCRAPE
            return self._get_video_details_via_scrape(video_id)

    def _get_video_details_via_scrape(self, video_id: str) -> Dict[str, Any]:
        """
        Get video details using web scraping as a fallback.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video details
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url)

            # Extract basic info
            title_pattern = r'<meta name="title" content="(.*?)">'
            title_match = re.search(title_pattern, response.text)
            title = title_match.group(1) if title_match else "Unknown Video"

            # Extract view count
            view_pattern = r'"viewCount":{"simpleText":"(.*?)"}'
            view_match = re.search(view_pattern, response.text)
            view_text = view_match.group(1) if view_match else "0"
            view_count = self._parse_count(view_text)

            # Extract like count
            like_pattern = r'"likeCount":"(.*?)"'
            like_match = re.search(like_pattern, response.text)
            like_count = int(like_match.group(1)) if like_match else 0

            # Extract channel info
            channel_pattern = r'"ownerChannelName":"(.*?)","uploadDate":"(.*?)"'
            channel_match = re.search(channel_pattern, response.text)
            channel_title = (
                channel_match.group(1) if channel_match else "Unknown Channel"
            )
            published_at = channel_match.group(2) if channel_match else ""

            # Extract description
            description_pattern = r'"shortDescription":"(.*?)"'
            description_match = re.search(description_pattern, response.text)
            description = description_match.group(1) if description_match else ""

            # Try to extract channel ID
            channel_id_pattern = r'"channelId":"(.*?)"'
            channel_id_match = re.search(channel_id_pattern, response.text)
            channel_id = channel_id_match.group(1) if channel_id_match else ""

            details = {
                "video_id": video_id,
                "title": title,
                "description": description,
                "published_at": published_at,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "tags": [],
                "category_id": "",
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "duration": "",
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": 0,
            }

            # Detect collaborations
            details["collaborators"] = self.detect_collaborators(description)

            return details
        except Exception as e:
            logger.error(f"Error scraping video details for {video_id}: {e}")
            return {
                "video_id": video_id,
                "title": "Unknown Video",
                "description": "",
                "collaborators": [],
            }

    def detect_collaborators(self, description: str) -> List[Dict[str, str]]:
        """
        Detect collaborators mentioned in the video description.

        Args:
            description: Video description

        Returns:
            List of collaborator dictionaries
        """
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

    # ============ Twitch Methods ============

    def get_twitch_status(self, channel_url_or_name: str) -> Dict[str, Any]:
        """
        Check if a Twitch channel is currently live.

        Args:
            channel_url_or_name: Twitch channel URL or name

        Returns:
            Dictionary with live status information
        """
        try:
            # Normalize URL
            if "twitch.tv/" not in channel_url_or_name:
                channel_url = f"https://www.twitch.tv/{channel_url_or_name}"
            else:
                channel_url = channel_url_or_name

            # Use ytlv to get Twitch live status
            twitch_data = ytlv_twitch(channel_url)

            # Extract channel name from URL
            channel_name = channel_url.split("/")[-1]

            # Convert to dictionary
            live_dict = {
                "status": "LIVE" if twitch_data.islive else None,
                "channel": channel_url,
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
            logger.error(f"Error getting Twitch status for {channel_url_or_name}: {e}")
            return {
                "status": None,
                "channel": channel_url_or_name,
                "platform": "twitch",
                "timestamp": None,
            }

    # ============ Platform-agnostic Methods ============

    def get_channel_by_platform(
        self, platform: str, channel_id_or_url: str
    ) -> Dict[str, Any]:
        """
        Get channel information based on platform type.

        Args:
            platform: Platform name ("youtube" or "twitch")
            channel_id_or_url: Channel ID or URL

        Returns:
            Dictionary with channel information
        """
        if platform.lower() == "youtube":
            return self.get_channel_info(channel_id_or_url)
        elif platform.lower() == "twitch":
            # Currently we have limited Twitch channel info capabilities
            # This will return basic info and live status
            twitch_live = self.get_twitch_status(channel_id_or_url)

            # Extract username from URL if needed
            username = channel_id_or_url
            if "twitch.tv/" in channel_id_or_url:
                username = channel_id_or_url.split("twitch.tv/")[-1].split("/")[0]

            return {
                "channel_id": username,
                "name": username,
                "description": "",
                "platform": "twitch",
                "channel_url": f"https://www.twitch.tv/{username}",
                "live_status": twitch_live["status"],
                "thumbnail": twitch_live.get("avatar", ""),
                "last_updated": time.time(),
            }
        else:
            logger.error(f"Unsupported platform: {platform}")
            return {}
