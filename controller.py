import asyncio
import logging
import time
import traceback

from googleapiclient.discovery import build

from database_schema import VtuberDatabase
from twitch_live import Twitch_Live_webscrap
from youtube_live import Youtube_api, Youtube_webscrap

log = logging.getLogger("vtuber_tracker")


class VtuberTrackerControl:
    def __init__(self, db, api_key, debug=False) -> None:
        self.db: VtuberDatabase = db
        self.debug = debug

        self.youtube_api = None
        if api_key:
            try:
                self.youtube_api = build("youtube", "v3", developerKey=api_key)
                log.info("Successfully initialized YouTube Data API v3 client")
            except Exception as e:
                log.error(f"Failed to initialize YouTube API client: {e}")
                self.api_quota_exceeded = True

        self.api_quota_exceeded = False
        if debug:
            self.channel_list = self.db.get_channelurl_list()[-10:]
        else:
            self.channel_list = self.db.get_channelurl_list()

        self.readylive = set()
        self.overtimelive = set()
        self.mainloop = asyncio.new_event_loop()

        self.api_units_used_today = 0
        self.api_quota_reset_time = time.time() + 86400
        self.max_api_units_per_day = 10000

        time.sleep(3)
        self.mainloop.create_task(self.start_getdata())
        self.mainloop.create_task(self.check_readylist())
        self.mainloop.run_forever()

    async def start_getdata(self):
        """Main loop for checking live status."""
        while True:
            starttime = time.time()
            checklist = [channel for channel in self.channel_list if channel not in self.readylive]

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
            log.info(f"Live status check completed in {int(alltime / 60)}m {int(alltime % 60)}s")
            log.info(
                f"Next check scheduled for {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime + 600))}"
            )

            await asyncio.sleep(600)
            self.update_channel_list()

    async def run(self, checklist):
        """Check live status for a list of channels."""
        tasks = []
        for channel_url in checklist:
            await asyncio.sleep(0.2)
            tasks.append(asyncio.create_task(self.check_live_status(channel_url)))
        if tasks:
            nolivelist = []
            results, _ = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            for result in results:
                try:
                    result_data = result.result()
                    if result_data is None:
                        log.warning(f"Result is None for {result}")
                        continue
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
            if nolivelist:
                log.info(f"Removing {len(nolivelist)} channels from live database")
                self.db.clean_nolive(nolivelist)

    async def check_live_status(self, channel_url):
        """Check live status for a single channel using YouTube API directly."""
        if time.time() > self.api_quota_reset_time:
            log.info("Resetting API quota usage counter")
            self.api_units_used_today = 0
            self.api_quota_reset_time = time.time() + 86400
            self.api_quota_exceeded = False

        if "twitch.tv" in channel_url:
            try:
                log.debug(f"Checking Twitch live status for {channel_url}")
                live_status = await Twitch_Live_webscrap().check(channel_url)
                return live_status
            except Exception as e:
                log.error(f"Error checking Twitch live status for {channel_url}: {e}")
                return {
                    "status": None,
                    "channel": channel_url,
                    "platform": "twitch",
                    "timestamp": None,
                }

        should_use_api = (
            not self.api_quota_exceeded
            and self.api_units_used_today < self.max_api_units_per_day
            and self.youtube_api is not None
        )

        if should_use_api:
            return await Youtube_api(self, self.youtube_api).check(channel_url)
        return await Youtube_webscrap().check(channel_url)

    async def check_readylist(self):
        """Periodically check the ready list for stale entries."""
        while True:
            log.info("Checking ready list for stale entries")
            cplist = self.readylive.copy()
            for channel_url in cplist:
                res = await self.check_live_status(channel_url)

                if res["status"] is None:
                    self.readylive.remove(channel_url)
                    log.warning(f"{channel_url} is no longer scheduled, removing from ready list")

            await asyncio.sleep(3600)

    async def wait_live(self, result):
        """Wait for a scheduled stream to go live."""
        if not result["timestamp"]:
            log.warning(f"No timestamp for scheduled stream: {result['channel']}")
            self.readylive.remove(result["channel"])
            return
        wait_time = int(result["timestamp"] - time.time())
        if wait_time <= 0:
            log.warning(f"Stream already past scheduled time: {result['channel']}")
            wait_time = 60
        log.info(f"Waiting {wait_time} seconds for {result['channel']} to go live")
        await asyncio.sleep(wait_time)
        channel_url = result["channel"]
        res = await self.check_live_status(channel_url)
        if res["status"] == "LIVE":
            log.info(f"{res['channel']} is now live")
            self.readylive.remove(result["channel"])
            self.db.update_live(result["channel"], res)
        else:
            log.info(f"{res['channel']} is not live yet, will retry every minute for 10 minutes")

            for i in range(10):
                res = await self.check_live_status(channel_url)

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
