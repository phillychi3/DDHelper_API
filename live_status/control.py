import time
import logging
from spider import Live_spider
from database import db
import asyncio
log = logging.getLogger("ddhelper_live")

class Live_spider_control():
    
    def __init__(self) -> None:
        self.channel_list = db.get_channelurl_list()
        self.readylive = []
        self.living = []
        time.sleep(3)
        self.main()
        while True:
            time.sleep(600)
            self.main()

    def main(self):
        checklist = self.channel_list.copy()
        for channel in checklist:
            if channel in self.readylive:
                checklist.remove(channel)
            if channel in self.living:
                checklist.remove(channel)
        if len(checklist) == 0:
            log.info("No channel to check")
            return
        log.info(f"Checking {len(checklist)} channels")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run(checklist))
        loop.close()

    async def run(self, checklist):
        tasks = []
        for channel in checklist:
            log.info(f"Now is checking {channel}")
            tasks.append(asyncio.create_task(Live_spider(channel)))
        for task in tasks:
            await task
        for task in tasks:
            result = task.result()
            if result["status"] == "OK":
                self.living.append(result["channel"])
                log.info(f"{result['channel']} is living")
            elif result["status"] == "LIVE_OFFLINE":
                self.readylive.append(result["channel"])
                log.info(f"{result['channel']} is reading to live")
            elif result["status"] == "NONE":
                continue
            else:
                print(result)
                log.error(f"fetch {result['channel']} error")
                continue
            db.update_live(result['channel'],result)


            




