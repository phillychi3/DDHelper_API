import asyncio
import logging
import time

from ytlv import twitch

log = logging.getLogger("vtuber_tracker")


class TwitchLiveInterface:
    async def check(self, channel_id_or_url: str):
        pass


class Twitch_Live_webscrap(TwitchLiveInterface):
    async def check(self, channel_url_or_name):
        try:
            if "twitch.tv/" not in channel_url_or_name:
                channel_url = f"https://www.twitch.tv/{channel_url_or_name}"
            else:
                channel_url = channel_url_or_name

            loop = asyncio.get_event_loop()
            twitch_data = await loop.run_in_executor(None, twitch, channel_url)

            live_dict = {
                "status": "LIVE" if twitch_data.islive else None,
                "channel": channel_url,
                "platform": "twitch",
                "timestamp": time.time() if twitch_data.islive else None,
            }

            if twitch_data.title:
                live_dict["title"] = twitch_data.title
            if twitch_data.picture:
                live_dict["thumbnail"] = twitch_data.picture
            if twitch_data.avatar:
                live_dict["avatar"] = twitch_data.avatar

            return live_dict

        except Exception as e:
            log.error(f"Error getting Twitch status for {channel_url_or_name}: {e}")
            return {
                "status": None,
                "channel": channel_url_or_name,
                "platform": "twitch",
                "timestamp": None,
            }
