import logging
import time
from typing import Any

from googleapiclient.errors import HttpError

from Vtuber import Vtuber
from ytlv import youtube as ytlv_youtube

log = logging.getLogger("vtuber_tracker")


class YoutubeLiveInterface:
    async def check(self, channel_id_or_url: str, channel_url: str):
        pass


class Youtube_Live_api(YoutubeLiveInterface):
    def __init__(self, controller: Any, api: Any = None):
        self.youtube_api = None
        self.controller = controller

        if api:
            self.youtube_api = api

    async def check(self, channel_url):
        try:
            channel_id = Vtuber().extract_channel_id(channel_url)
            log.debug(f"Using YouTube API to check live status for {channel_id}")
            self.controller.api_units_used_today += 100
            live_request = self.youtube_api.search().list(
                part="snippet",
                channelId=channel_id,
                eventType="live",
                type="video",
                maxResults=1,
            )
            live_response = live_request.execute()

            if len(live_response.get("items", [])) > 0:
                live_video = live_response["items"][0]
                return {
                    "status": "LIVE",
                    "channel": channel_url,
                    "video_id": live_video["id"]["videoId"],
                    "title": live_video["snippet"]["title"],
                    "thumbnail": live_video["snippet"]["thumbnails"]["high"]["url"],
                    "platform": "youtube",
                    "timestamp": time.time(),
                }

            self.controller.api_units_used_today += 100
            upcoming_request = self.youtube_api.search().list(
                part="snippet",
                channelId=channel_id,
                eventType="upcoming",
                type="video",
                maxResults=1,
            )
            upcoming_response = upcoming_request.execute()

            if len(upcoming_response.get("items", [])) > 0:
                upcoming_video = upcoming_response["items"][0]
                self.controller.api_units_used_today += 1
                video_request = self.youtube_api.videos().list(
                    part="liveStreamingDetails", id=upcoming_video["id"]["videoId"]
                )
                video_response = video_request.execute()

                if "items" in video_response and video_response["items"]:
                    scheduled_time = video_response["items"][0]["liveStreamingDetails"][
                        "scheduledStartTime"
                    ]
                    scheduled_timestamp = time.mktime(
                        time.strptime(
                            scheduled_time.replace("Z", "GMT"),
                            "%Y-%m-%dT%H:%M:%S%Z",
                        )
                    )
                    return {
                        "status": "READY_TO_LIVE",
                        "channel": channel_url,
                        "video_id": upcoming_video["id"]["videoId"],
                        "title": upcoming_video["snippet"]["title"],
                        "thumbnail": upcoming_video["snippet"]["thumbnails"]["high"]["url"],
                        "platform": "youtube",
                        "timestamp": scheduled_timestamp,
                    }
            return {
                "status": None,
                "channel": channel_url,
                "platform": "youtube",
                "timestamp": None,
            }

        except HttpError as e:
            if e.resp.status in [403, 429]:
                log.warning(f"YouTube API quota exceeded, switching to scraping method: {e}")
                self.controller.api_quota_exceeded = True
            else:
                log.error(f"YouTube API error: {e}")
        except Exception as e:
            log.error(f"Error using YouTube API to check live status for {channel_id}: {e}")


class Youtube_Live_webscrap(YoutubeLiveInterface):
    async def check(self, channel_url):
        """Fallback to scraping method when API is unavailable or quota exceeded."""
        try:
            log.debug(f"Using pure scraping method to check live status for {channel_url}")
            try:
                live_data = ytlv_youtube(channel_url)

                status = getattr(live_data, "status", None)
                timestamp = getattr(live_data, "timestamp", None)

                if timestamp is not None and (
                    int(timestamp) - time.time() > 60 * 60 * 24  # 超過24小時
                    or int(timestamp) - time.time() < 0  # 已過期
                ):
                    status = None

                live_dict = {
                    "status": status,
                    "channel": channel_url,
                    "platform": "youtube",
                    "timestamp": timestamp,
                }

                title = getattr(live_data, "title", None)
                if title:
                    live_dict["title"] = title

                picture = getattr(live_data, "picture", None)
                if picture:
                    live_dict["thumbnail"] = picture

                link = getattr(live_data, "link", None)
                if link and "youtube.com/watch?v=" in link:
                    video_id = link.split("v=")[1].split("&")[0]
                    live_dict["video_id"] = video_id

                return live_dict
            except Exception as e:
                log.error(f"Error with pure scraping for YouTube: {e}")
                return {
                    "status": None,
                    "channel": channel_url,
                    "platform": "youtube",
                    "timestamp": None,
                }
        except Exception as e:
            log.error(f"Error checking live status via scraping for {channel_url}: {e}")
            return {
                "status": None,
                "channel": channel_url,
                "platform": "youtube" if "twitch.tv" not in channel_url else "twitch",
                "timestamp": None,
            }
