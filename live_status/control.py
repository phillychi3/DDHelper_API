import time
import logging
from spider import Live_spider
from database import db
import asyncio

log = logging.getLogger("ddhelper_live")


class Live_spider_control:
    def __init__(self, debug=False) -> None:
        if debug:
            self.channel_list = db.get_channelurl_list()[-10:]
        else:
            self.channel_list = db.get_channelurl_list()
        self.mainloop = asyncio.new_event_loop()
        self.readylive = set()
        self.overtimelive = set()
        time.sleep(3)
        self.mainloop.create_task(self.start_getdata())
        self.mainloop.run_forever()

    def update_channel_list(self):
        self.channel_list = db.get_channelurl_list()

    async def start_getdata(self):
        while True:
            starttime = time.time()
            checklist = [
                channel
                for channel in self.channel_list
                if channel not in self.readylive
            ]
            log.info(
                f"work is start at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(starttime))}"
            )
            if not checklist:
                log.info("No channel to check")
            else:
                log.info(f"Checking {len(checklist)} channels")
                await self.run(checklist)
            endtime = time.time()
            log.info(
                f"work is finish at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime))}"
            )
            alltime = endtime - starttime
            log.info(f"work is finish, use {int(alltime/60)}m {int(alltime%60)}s")
            log.info(
                f"next work will be stard at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime+600))}"
            )
            await asyncio.sleep(600)
            self.update_channel_list()

    async def run(self, checklist):
        tasks = [asyncio.create_task(Live_spider(channel)) for channel in checklist]
        results, _ = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        nolivelist = []
        for result in results:
            try:
                result = result.result()
                if result["status"] == "LIVE":
                    log.info(f"{result['channel']} is living")
                elif result["status"] == "READY_TO_LIVE":
                    self.readylive.add(result["channel"])
                    log.info(f"{result['channel']} is ready to live")
                    self.mainloop.create_task(self.wait_live(result))

                elif result["status"] == None:
                    nolivelist.append(result["channel"])
                    continue
                else:
                    print(result)
                    log.error(f"fetch {result['channel']} error")
                    continue
                db.update_live(result["channel"], result)
                db.clean_nolive(nolivelist)
            except Exception as e:
                log.error(f"fetch some error")
                log.error(e)

    async def wait_live(self, result):
        # 這裡判斷有些問題，就算過了10分鐘，系統還是會在把他加入readylive
        print(int(result["timestamp"])-time.time())
        await asyncio.sleep(int(result["timestamp"])-time.time())
        res = await Live_spider(result["channel"])
        if res["status"] == "LIVE":
            log.info(f"{res['channel']} is living")
            self.readylive.remove(result["channel"])
            db.update_live(result["channel"], res)
        else:
            log.info(f"{res['channel']} is not living, retry in 10m")
            for i in range(10):
                res = await Live_spider(result["channel"])
                if res["status"] == "LIVE":
                    log.info(f"{res['channel']} is living")
                    self.readylive.remove(result["channel"])
                    db.update_live(result["channel"], res)
                    return
                await asyncio.sleep(60)
            log.info(f"{res['channel']} is not living, remove from readylist")
            self.readylive.remove(result["channel"])
            db.update_live(result["channel"], res)
        return
