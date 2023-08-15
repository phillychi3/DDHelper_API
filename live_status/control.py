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
            log.info(f"work is start at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
            if not checklist:
                log.info("No channel to check")
            else:
                log.info(f"Checking {len(checklist)} channels")
                await self.run(checklist)
            log.info(f"work is finish at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
            await asyncio.sleep(600)

    async def run(self, checklist):
        tasks = [asyncio.create_task(Live_spider(channel)) for channel in checklist]
        # results = await asyncio.gather(*tasks)
        results,_ = await asyncio.wait(tasks,return_when=asyncio.ALL_COMPLETED)
        for result in results:
            result = result.result()
            if result["status"] == "LIVE":
                log.info(f"{result['channel']} is living")
            elif result["status"] == "READY_TO_LIVE":
                self.readylive.add(result["channel"])
                log.info(f"{result['channel']} is ready to live")
                self.mainloop.create_task(self.wait_live(result))

            elif result["status"] ==None:
                continue
            else:
                print(result)
                log.error(f"fetch {result['channel']} error")
                continue
            db.update_live(result["channel"], result)

    async def wait_live(self, result):
        print(int(result["timestamp"])-time.time())
        await asyncio.sleep(int(result["timestamp"])-time.time())
        res = await Live_spider(result["channel"])
        if res["status"] == "LIVE":
            log.info(f"{res['channel']} is living")
            self.readylive.remove(result["channel"])
            db.update_live(result["channel"], res)
        else:
            log.info(f"{res['channel']} is not living, wait more 10m")
            await asyncio.sleep(600)
            res = await Live_spider(result["channel"])
            if res["status"] == "LIVE":
                log.info(f"{res['channel']} is living")
                self.readylive.remove(result["channel"])
                db.update_live(result["channel"], res)
            else:
                log.info(f"{res['channel']} is not living, remove wait list")
                self.readylive.remove(result["channel"])
                db.update_live(result["channel"], res)
