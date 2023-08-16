import asyncio
import time
from dataclasses import asdict
from ytlv import twitch, youtube


async def Live_spider(url):
    if "youtube.com" in url:
        live = youtube(str(url))
        live = asdict(live)
        if (
            live["timestamp"] != None
            and (int(live["timestamp"]) - time.time() > 60 * 60 * 24
            or int(live["timestamp"]) - time.time() < 0)
        ):
            live["status"] = None
    elif "twitch.tv" in url:
        live = twitch(str(url))
        live = asdict(live)
    
    live.update({"channel": url})
    await asyncio.sleep(0.2)
    return live
