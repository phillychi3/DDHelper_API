import asyncio
import time
import logging
from dataclasses import asdict
from ytlv import twitch, youtube

log = logging.getLogger("ddhelper_live")

async def Live_spider(url):
    log.debug(f"start check {url}")
    if "youtube.com" in url:
        live = youtube(str(url))
        live = asdict(live)
        if (
            live["timestamp"] != None
            and (int(live["timestamp"]) - time.time() > 60 * 60 * 24
            or int(live["timestamp"]) - time.time() < 0)
        ):
            live["status"] = None
        live["platform"] = "youtube"
    elif "twitch.tv" in url:
        live = twitch(str(url))
        live = asdict(live)
        live["platform"] = "twitch"
    live.update({"channel": url})
    await asyncio.sleep(0.2)
    return live
