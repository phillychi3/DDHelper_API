from ytlv import youtube, twitch
import asyncio
import time

async def Live_spider(url):
    if "youtube.com" in url:
        live = youtube(str(url))
        if live["timestamp"]!="NONE"and int(live["timestamp"])-time.time() > 60*60*24:
            live["status"] = "NONE"
    elif "twitch.tv" in url:
        live = twitch(str(url))
    live.update({"channel": url})
    await asyncio.sleep(1)
    return live
