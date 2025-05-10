import logging
import re
import time
from typing import Any

from googleapiclient.errors import HttpError
import requests

from vtuber import extract_channel_id, extract_channel_mouse_id
from ytlv import youtube as ytlv_youtube
from vtuber import parse_count

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
            channel_id = extract_channel_id(channel_url)
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

    def get_channel_info(self, channel_id: str) -> dict[str, Any]:
        """
        Get channel info using web scraping as a fallback.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dictionary with channel information
        """
        try:
            url = f"https://www.youtube.com/{channel_id}"
            response = requests.get(url)

            # Extract subscriber count
            subscriber_pattern = r'"subscriberCountText":\{"simpleText":"(.*?)"'
            subscriber_match = re.search(subscriber_pattern, response.text)
            subscriber_text = subscriber_match.group(1) if subscriber_match else "0"
            subscriber_count = parse_count(subscriber_text)

            # Extract view count
            view_pattern = r'"viewCountText":\{"simpleText":"(.*?)"'
            view_match = re.search(view_pattern, response.text)
            view_text = view_match.group(1) if view_match else "0"
            view_count = parse_count(view_text)

            # Extract channel name
            title_pattern = r'<meta name="title" content="(.*?)">'
            title_match = re.search(title_pattern, response.text)
            channel_name = title_match.group(1) if title_match else "Unknown Channel"

            # Extract description
            description_pattern = r'"description":\{"simpleText":"(.*?)"\}'
            description_match = re.search(description_pattern, response.text)
            description = description_match.group(1) if description_match else ""

            # Extract thumbnail
            thumbnail_pattern = r'"avatar":\{"thumbnails":\[\{"url":"(.*?)"'
            thumbnail_match = re.search(thumbnail_pattern, response.text)
            thumbnail = thumbnail_match.group(1) if thumbnail_match else ""

            # Try to extract handle
            handle_pattern = r'"canonicalChannelUrl":"https://www.youtube.com/@([^"]+)"'
            handle_match = re.search(handle_pattern, response.text)
            handle = handle_match.group(1) if handle_match else ""

            return {
                "channel_id": channel_id,
                "name": channel_name,
                "description": description,
                "custom_url": f"@{handle}" if handle else "",
                "published_at": "",  # Can't reliably get this from scraping
                "thumbnail": thumbnail,
                "country": "",  # Can't reliably get this from scraping
                "view_count": view_count,
                "subscriber_count": subscriber_count,
                "hidden_subscriber_count": subscriber_count == 0,
                "video_count": 0,  # Can't reliably get this from scraping
                "company": "Unknown",  # Need manual categorization
                "activity_status": "active",
                "debut_date": "",  # Can't reliably get this from scraping
                "platform": "youtube",
                "channel_url": f"https://www.youtube.com/{channel_id}",
                "handle": handle,
                "last_updated": time.time(),
            }
        except Exception as e:
            log.error(f"Error scraping channel {channel_id}: {e}")
            return {
                "channel_id": channel_id,
                "name": "Unknown Channel",
                "platform": "youtube",
                "channel_url": f"https://www.youtube.com/{channel_id}",
                "last_updated": time.time(),
            }


if __name__ == "__main__":
    channel_url = "https://www.youtube.com/@stringflowers"

    youtube_live = Youtube_Live_webscrap()
    chid = extract_channel_mouse_id(channel_url)
    test = youtube_live.get_channel_info(chid)
    print(test)
