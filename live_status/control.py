import time
import logging
from spider import Live_spider
from database import db
import asyncio
log = logging.getLogger("eternal")

class Live_spider_control():
    
    def __init__(self) -> None:
        self.channel_list = db.get_channel_list()
        self.readylive = []
        self.living = []    
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
        log.info(f"Checking {checklist} channels")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run(checklist))
        loop.close()

    async def run(self, checklist):
        tasks = []
        for channel in checklist:
            tasks.append(asyncio.create_task(Live_spider(channel)))
        for task in tasks:
            await task
        for task in tasks:
            ...
            # if task.result() == "readylive":
            #     self.readylive.append(task.get_name())
            # elif task.result() == "living":
            #     self.living.append(task.get_name())




