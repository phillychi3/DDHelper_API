import asyncio
import datetime
import logging
import time
import traceback

from googleapiclient.discovery import build

from database_schema import VtuberDatabase
from twitch_live import Twitch_Live_webscrap
from youtube_live import Youtube_api, Youtube_webscrap

log = logging.getLogger("vtuber_tracker")


class VtuberTrackerControl:
    def __init__(self, db: VtuberDatabase, api_key, debug=False) -> None:
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

        self.next_channel_update_time = self._get_next_midnight()

        self.status = {
            "current_task": "initializing",
            "current_channel": None,
            "total_channels": len(self.channel_list),
            "checked_channels": 0,
            "last_check_start": None,
            "last_check_end": None,
            "next_check_time": None,
            "api_quota_used": 0,
            "api_quota_limit": self.max_api_units_per_day,
            "api_quota_reset_time": self.api_quota_reset_time,
            "ready_live_count": 0,
            "is_running": True,
            "errors": [],
            "next_channel_update_time": self.next_channel_update_time,
            "last_channel_update": None,
        }

        time.sleep(3)
        self.mainloop.create_task(self.start_getdata())
        self.mainloop.create_task(self.check_readylist())
        self.mainloop.create_task(self.schedule_channel_update())
        self.mainloop.run_forever()

    def _get_next_midnight(self):
        """計算下一次午夜 12:00 的時間戳"""
        now = datetime.datetime.now()
        if now.hour >= 0:
            next_midnight = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + datetime.timedelta(days=1)
        else:
            next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return next_midnight.timestamp()

    def get_status(self):
        """獲取當前 controller 狀態"""
        self.status["api_quota_used"] = self.api_units_used_today
        self.status["ready_live_count"] = len(self.readylive)
        self.status["api_quota_exceeded"] = self.api_quota_exceeded
        self.status["next_channel_update_time"] = self.next_channel_update_time
        return self.status.copy()

    async def schedule_channel_update(self):
        """定時執行頻道資料更新的排程器"""
        while True:
            current_time = time.time()
            if current_time >= self.next_channel_update_time:
                log.info("開始執行每日頻道資料更新...")
                self.status["current_task"] = "updating_channel_data"
                try:
                    await self.update_channel_data()
                    self.status["last_channel_update"] = current_time
                    log.info("每日頻道資料更新完成")
                except Exception as e:
                    log.error(f"頻道資料更新失敗: {e}")
                    error_info = {
                        "timestamp": time.time(),
                        "error": f"Channel update failed: {str(e)}",
                        "traceback": traceback.format_exc(),
                    }
                    self.status["errors"].append(error_info)
                    if len(self.status["errors"]) > 10:
                        self.status["errors"].pop(0)
                self.next_channel_update_time = self._get_next_midnight()
                self.status["next_channel_update_time"] = self.next_channel_update_time
                log.info(
                    f"下次頻道資料更新時間: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.next_channel_update_time))}"
                )
            await asyncio.sleep(3600)

    async def start_getdata(self):
        """Main loop for checking live status."""
        while True:
            starttime = time.time()
            self.status["current_task"] = "checking_live_status"
            self.status["last_check_start"] = starttime
            self.status["checked_channels"] = 0
            self.status["current_channel"] = None

            checklist = [channel for channel in self.channel_list if channel not in self.readylive]

            log.info(
                f"Live status check started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(starttime))}"
            )

            if not checklist:
                log.info("No channels to check")
            else:
                log.info(f"Checking {len(checklist)} channels")
                try:
                    await self.run(checklist)
                except Exception as e:
                    log.error(f"Error during live status check: {e}")
                    error_info = {
                        "timestamp": time.time(),
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }
                    self.status["errors"].append(error_info)
                    if len(self.status["errors"]) > 10:
                        self.status["errors"].pop(0)

            endtime = time.time()
            self.status["last_check_end"] = endtime
            self.status["next_check_time"] = endtime + 600
            self.status["current_task"] = "waiting"
            self.status["current_channel"] = None

            log.info(
                f"Live status check finished at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime))}"
            )
            alltime = endtime - starttime
            log.info(f"Live status check completed in {int(alltime / 60)}m {int(alltime % 60)}s")
            log.info(
                f"Next check scheduled for {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime + 600))}"
            )

            await asyncio.sleep(600)

    async def run(self, checklist):
        """Check live status for a list of channels."""
        tasks = []
        for i, channel_url in enumerate(checklist):
            self.status["current_channel"] = channel_url
            self.status["checked_channels"] = i
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
                    error_info = {
                        "timestamp": time.time(),
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }
                    self.status["errors"].append(error_info)
                    if len(self.status["errors"]) > 10:
                        self.status["errors"].pop(0)
                    # traceback.print_exc()

            if nolivelist:
                log.info(f"Removing {len(nolivelist)} channels from live database")
                try:
                    self.db.clean_nolive(nolivelist)
                except Exception as e:
                    log.error(f"Failed to clean nolive channels from database: {e}")

        self.status["checked_channels"] = len(checklist)

    async def update_channel_data(self):
        """Update channel data from the database."""
        log.info("Updating channel data from database")
        try:
            old_channel_count = len(self.channel_list)
            self.channel_list = self.db.get_channelurl_list()
            update_count = 0
            for channel_url in self.channel_list:
                try:
                    channel_data = Youtube_webscrap().get_channel_info(channel_url)
                    if channel_data:
                        update_fields = {
                            "subscriber_count": channel_data.get("subscriber_count", 0),
                            "view_count": channel_data.get("view_count", 0),
                            "video_count": channel_data.get("video_count", 0),
                        }
                        self.db.update_channel_by_url(channel_url, update_fields)
                        update_count += 1
                        log.debug(f"Updated channel stats for {channel_url}")
                except Exception as e:
                    log.error(f"Error updating individual channel {channel_url}: {e}")
                await asyncio.sleep(0.5)
            log.info(
                f"Updated {update_count} channels out of {len(self.channel_list)} total channels"
            )
            self.status["total_channels"] = len(self.channel_list)
            if len(self.channel_list) != old_channel_count:
                log.info(
                    f"Channel count changed from {old_channel_count} to {len(self.channel_list)}"
                )

        except Exception as e:
            log.error(f"Error updating channel data: {e}")
            error_info = {
                "timestamp": time.time(),
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            self.status["errors"].append(error_info)
            if len(self.status["errors"]) > 10:
                self.status["errors"].pop(0)

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

                if res is None or res["status"] is None:
                    self.readylive.discard(channel_url)
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
        if res is None:
            log.warning(f"check_live_status returned None for {channel_url}, skipping")
            return
        if res["status"] == "LIVE":
            log.info(f"{res['channel']} is now live")
            self.readylive.remove(result["channel"])
            self.db.update_live(result["channel"], res)
        else:
            log.info(f"{res['channel']} is not live yet, will retry every minute for 10 minutes")

            for i in range(10):
                res = await self.check_live_status(channel_url)

                if res is None:
                    log.warning(f"check_live_status returned None for {channel_url} on retry {i + 1}, skipping")
                    await asyncio.sleep(60)
                    continue
                if res["status"] == "LIVE":
                    log.info(f"{res['channel']} is now live after retry {i + 1}")
                    self.readylive.remove(result["channel"])
                    self.db.update_live(result["channel"], res)
                    return
                await asyncio.sleep(60)
            log.info(
                f"{channel_url} did not go live within retry window, removing from ready list"
            )
            self.readylive.discard(result["channel"])
            if res is not None:
                self.db.update_live(result["channel"], res)
