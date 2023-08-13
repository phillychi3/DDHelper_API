from ytlv import youtube, twitch
import asyncio

async def Live_spider(url):
    if "youtube.com" in url:
        live = youtube(str(url))
    elif "twitch.tv" in url:
        live = twitch(str(url))
    live.update({"channel": url})
    await asyncio.sleep(1)
    return live
