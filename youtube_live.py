import logging
import re
import time
from typing import Any

from googleapiclient.errors import HttpError
import requests

from vtuber import extract_channel_id, extract_company
from ytlv import youtube as ytlv_youtube
from vtuber import parse_count

log = logging.getLogger("vtuber_tracker")


class YoutubeLiveInterface:
    async def check(self, channel_url: str):
        pass


class Youtube_api(YoutubeLiveInterface):
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
            return {"status": None, "channel": channel_url, "platform": "youtube", "timestamp": None}
        except Exception as e:
            log.error(f"Error using YouTube API to check live status for {channel_id}: {e}")
            return {"status": None, "channel": channel_url, "platform": "youtube", "timestamp": None}


class Youtube_webscrap(YoutubeLiveInterface):
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

    def get_channel_info(self, channel_url: str) -> dict[str, Any]:
        """
        Get channel info using web scraping as a fallback.

        Args:
            channel_url: YouTube channel URL

        Returns:
            Dictionary with channel information
        """
        try:
            channel_id = extract_channel_id(channel_url)
            url = f"https://www.youtube.com/channel/{channel_id}"
            response = requests.get(url)

            # with open("debug.html", "w", encoding="utf-8") as f:
            #     f.write(response.text)

            subscriber_pattern = r']},{"metadataParts":\[{"text":{"((?!.*查看完整播放清單).*?)位訂閱者"},"accessibilityLabel":".*?位訂閱者"'
            subscriber_match = re.search(subscriber_pattern, response.text)
            subscriber_text = subscriber_match.group(1) if subscriber_match else "0"
            subscriber_count = parse_count(subscriber_text)

            # Extract view count
            view_pattern = r'"viewCountText":\{"simpleText":"(.*?)"'
            view_match = re.search(view_pattern, response.text)
            view_text = view_match.group(1) if view_match else "0"
            view_count = parse_count(view_text)

            # Extract channel name
            title_pattern = r"<title>(.*?) - YouTube</title>"
            title_match = re.search(title_pattern, response.text)
            channel_name = title_match.group(1) if title_match else "Unknown Channel"

            # Extract description
            description_pattern = (
                r'{"descriptionPreviewViewModel":{"description":{"content":"(.*?)"}'
            )
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

            # Try to extract video count
            video_count_pattern = r'訂閱者"},{"text":{"content":"(.*?) 部影片","styleRuns":\[{"startIndex":0,"length":8}\]'

            video_count_match = re.search(video_count_pattern, response.text)
            video_count = int(video_count_match.group(1)) if video_count_match else 0

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
                "video_count": video_count,
                "company": extract_company(description),
                "activity_status": "active",
                "debut_date": "",  # Can't reliably get this from scraping
                "platform": "youtube",
                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                "handle": handle,
                "last_updated": time.time(),
            }
        except Exception as e:
            log.error(f"Error scraping channel {channel_id}: {e}")
            raise e
            # return {
            #     "channel_id": channel_id,
            #     "name": "Unknown Channel",
            #     "platform": "youtube",
            #     "channel_url": f"https://www.youtube.com/{channel_id}",
            #     "last_updated": time.time(),
            # }

    def get_video_details(self, video_id: str) -> dict[str, Any]:
        """
        Get video details using web scraping as a fallback.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video details
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url)

            # Extract basic info
            title_pattern = r'<meta name="title" content="(.*?)">'
            title_match = re.search(title_pattern, response.text)
            title = title_match.group(1) if title_match else "Unknown Video"

            # Extract view count
            view_pattern = r'"viewCount":{"simpleText":"(.*?)"}'
            view_match = re.search(view_pattern, response.text)
            view_text = view_match.group(1) if view_match else "0"
            view_count = parse_count(view_text)

            # Extract like count
            like_pattern = r'"likeCount":"(.*?)"'
            like_match = re.search(like_pattern, response.text)
            like_count = int(like_match.group(1)) if like_match else 0

            # Extract channel info
            channel_pattern = r'"ownerChannelName":"(.*?)","uploadDate":"(.*?)"'
            channel_match = re.search(channel_pattern, response.text)
            channel_title = channel_match.group(1) if channel_match else "Unknown Channel"
            published_at = channel_match.group(2) if channel_match else ""

            # Extract description
            description_pattern = r'"shortDescription":"(.*?)"'
            description_match = re.search(description_pattern, response.text)
            description = description_match.group(1) if description_match else ""

            # Try to extract channel ID
            channel_id_pattern = r'"channelId":"(.*?)"'
            channel_id_match = re.search(channel_id_pattern, response.text)
            channel_id = channel_id_match.group(1) if channel_id_match else ""

            details = {
                "video_id": video_id,
                "title": title,
                "description": description,
                "published_at": published_at,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "tags": [],
                "category_id": "",
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "duration": "",
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": 0,
            }

            # Detect collaborations
            details["collaborators"] = self.detect_collaborators(description)

            return details
        except Exception as e:
            log.error(f"Error scraping video details for {video_id}: {e}")
            return {
                "video_id": video_id,
                "title": "Unknown Video",
                "description": "",
                "collaborators": [],
            }

    def detect_collaborators(self, description: str) -> list[dict[str, str]]:
        """
        Detect collaborators mentioned in the video description.

        Args:
            description: Video description

        Returns:
            List of collaborator dictionaries
        """
        collaborators = []

        youtube_patterns = [
            r"(?:https?://)?(?:www\.)?youtube\.com/(?:channel/|c/|@)([^\s/]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/user/([^\s/]+)",
        ]

        for pattern in youtube_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if not any(c["channel_id"] == match for c in collaborators):
                    collaborators.append({"channel_id": match, "platform": "youtube"})

        mention_patterns = [
            r"@([A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_])",
            r"＠([A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_])",
        ]

        for pattern in mention_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if match and not any(c["channel_id"] == match for c in collaborators):
                    collaborators.append(
                        {
                            "channel_id": match,
                            "platform": "youtube_handle",
                        }
                    )

        collab_patterns = [
            r"(?:collab|collaboration|コラボ|合作).*?(?:with|w/|と)\s*@([A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_])",
            r"(?:ft\.|featuring|出演者).*?@([A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_])",
            r"(?:guest|ゲスト|來賓).*?@([A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_])",
        ]

        for pattern in collab_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match and not any(c["channel_id"] == match for c in collaborators):
                    collaborators.append(
                        {
                            "channel_id": match,
                            "platform": "collaboration_mention",
                        }
                    )

        return collaborators


if __name__ == "__main__":
    youtube_live = Youtube_webscrap()
    channel_url = "https://www.youtube.com/channel/UCdn5BQ06XqgXoAxIhbqw5Rg"

    chid = extract_channel_id(channel_url)
    test = youtube_live.get_channel_info(chid)
    print(test)

    # video_id = "MUt3DIyXieU"
    # video_details = youtube_live.get_video_details(video_id)
    # print(video_details)
