import time
import logging
from spider import Live_spider
from database import db
import asyncio

log = logging.getLogger("ddhelper_live")


class Live_spider_control:
    def __init__(self) -> None:
        self.channel_list = db.get_channelurl_list()
        self.mainloop = asyncio.new_event_loop()
        self.readylive = set()
        time.sleep(3)
        self.mainloop.create_task(self.start_getdata())
        self.mainloop.run_forever()

    async def start_getdata(self):
        while True:
            checklist = [channel for channel in self.channel_list if channel not in self.readylive]
            if not checklist:
                log.info("No channel to check")
            else:
                log.info(f"Checking {len(checklist)} channels")
                await self.run(checklist)
            await asyncio.sleep(600)

    async def run(self, checklist):
        tasks = [asyncio.create_task(Live_spider(channel)) for channel in checklist]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result["status"] == "OK":
                log.info(f"{result['channel']} is living")
            elif result["status"] == "LIVE_OFFLINE":
                self.readylive.add(result["channel"])
                log.info(f"{result['channel']} is ready to live")
                self.mainloop.create_task(self.wait_live(result))

            elif result["status"] == "NONE":
                continue
            else:
                print(result)
                log.error(f"fetch {result['channel']} error")
                continue
            db.update_live(result["channel"], result)

    async def wait_live(self, result):
        await asyncio.sleep(int(result["timestamp"])-time.time())
        res = Live_spider(result["channel"])
        if res["status"] == "OK":
            log.info(f"{res['channel']} is living")
            self.readylive.remove(result["channel"])
            db.update_live(result["channel"], res)
        else:
            log.info(f"{res['channel']} is not living, wait more 10m")
            await asyncio.sleep(600)
            res = Live_spider(result["channel"])
            if res["status"] == "OK":
                log.info(f"{res['channel']} is living")
                self.readylive.remove(result["channel"])
                db.update_live(result["channel"], res)
            else:
                log.info(f"{res['channel']} is not living, remove wait list")
                self.readylive.remove(result["channel"])
                db.update_live(result["channel"], res)
