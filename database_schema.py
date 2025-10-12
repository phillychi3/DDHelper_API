import logging

from pymongo import ASCENDING, TEXT, IndexModel, MongoClient
from pymongo.server_api import ServerApi

logger = logging.getLogger("VtuberDatabase")


class VtuberDatabase:
    def __init__(self, connection_string: str):
        self.client = MongoClient(connection_string, server_api=ServerApi("1"))
        self.db = self.client.vtuber
        self.live_db = self.client.live
        self.init_collections()

    def init_collections(self):
        """Initialize the database collections and indexes."""
        # Vtuber channels collection
        if "channel" not in self.db.list_collection_names():
            self.db.create_collection("channel")

            # Create indexes
            channel_indexes = [
                IndexModel([("channel_id", ASCENDING)], unique=True),
                IndexModel([("name", TEXT), ("company", TEXT), ("country", TEXT)]),
                IndexModel([("channel_url", ASCENDING)], unique=True),
            ]

            self.db.channel.create_indexes(channel_indexes)

        # Videos collection
        if "videos" not in self.db.list_collection_names():
            self.db.create_collection("videos")

            # Create indexes
            video_indexes = [
                IndexModel([("video_id", ASCENDING)], unique=True),
                IndexModel([("channel_id", ASCENDING)]),
                IndexModel([("published_at", ASCENDING)]),
                IndexModel([("title", TEXT), ("description", TEXT)]),
                IndexModel([("collaborators.channel_id", ASCENDING)]),
            ]

            self.db.videos.create_indexes(video_indexes)

        # Live streams collection
        if "live" not in self.live_db.list_collection_names():
            self.live_db.create_collection("live")

            # Create indexes
            live_indexes = [
                IndexModel([("channel", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("timestamp", ASCENDING)]),
                IndexModel([("platform", ASCENDING)]),
            ]

            self.live_db.live.create_indexes(live_indexes)

    def insert_channel(self, channel_data):
        """Insert or update a channel in the database."""
        try:
            channel_url = channel_data.get("channel_url")
            if not channel_url:
                logger.error("Cannot insert channel without channel_url")
                return False

            existing_channel = self.db.channel.find_one({"channel_url": channel_url})

            update_data = channel_data.copy()

            if existing_channel:
                if "company" in existing_channel and existing_channel["company"]:
                    update_data.pop("company", None)
                if "country" in existing_channel and existing_channel["country"]:
                    update_data.pop("country", None)

            self.db.channel.update_one(
                {"channel_url": channel_url}, {"$set": update_data}, upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error inserting channel: {e}")
            return False

    def get_channel(self, channel_id):
        """Get a channel from the database by ID."""
        return self.db.channel.find_one({"channel_id": channel_id})

    def get_channelurl_list(self):
        """Get a list of all channel URLs."""
        return [i["channel_url"] for i in self.db.channel.find()]

    def get_channels(self):
        """Get all channels with basic info."""
        vtubers = []
        for i in self.db.channel.find():
            vtubers.append(
                {
                    "name": i.get("name", ""),
                    "company": i.get("company", ""),
                    "country": i.get("country", ""),
                    "channel_url": i.get("channel_url", ""),
                    "platform": i.get("platform", ""),
                    "subscriber_count": i.get("subscriber_count", 0),
                    "view_count": i.get("view_count", 0),
                    "video_count": i.get("video_count", 0),
                    "activity_status": i.get("activity_status", ""),
                    "debut_date": i.get("debut_date", ""),
                    "thumbnail": i.get("thumbnail", ""),
                    "channel_id": i.get("channel_id", ""),
                }
            )
        return vtubers

    def get_channels_by_filter(self, filter_dict):
        """Get channels that match a filter."""
        return list(self.db.channel.find(filter_dict))

    def update_channel(self, channel, data):
        """Update a channel by name."""
        self.db.channel.update_one({"name": channel}, {"$set": data})

    def replace_channel(self, channel, data):
        """Replace a channel document."""
        self.db.channel.replace_one({"name": channel}, data)

    def delete_channel(self, channel):
        """Delete a channel by name."""
        self.db.channel.delete_one({"name": channel})

    def get_one_channel(self, channel):
        """Get a channel by name."""
        return self.db.channel.find_one({"name": channel})

    def insert_video(self, video_data):
        """Insert or update a video in the database."""
        try:
            video_id = video_data.get("video_id")
            if not video_id:
                logger.error("Cannot insert video without video_id")
                return False

            self.db.videos.update_one({"video_id": video_id}, {"$set": video_data}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"Error inserting video: {e}")
            return False

    def get_video(self, video_id):
        """Get a video from the database by ID."""
        return self.db.videos.find_one({"video_id": video_id})

    def get_channel_videos(self, channel_id, limit=50, skip=0):
        """Get videos from a specific channel."""
        return list(
            self.db.videos.find({"channel_id": channel_id})
            .sort("published_at", -1)
            .skip(skip)
            .limit(limit)
        )

    def reset_live(self):
        """Reset all live stream data."""
        self.live_db.live.delete_many({})

    def get_one_live(self, channel):
        """Get live status for a channel."""
        return self.live_db.live.find_one({"channel": channel})

    def getlivefromstatus(self, status):
        """Get all channels with a specific live status."""
        return self.live_db.live.find({"status": status})

    def update_live(self, channel, data):
        """Update live status for a channel."""
        try:
            if self.get_one_live(channel) is None:
                self.live_db.live.insert_one(data)
            else:
                self.live_db.live.replace_one({"channel": channel}, data)
            return True
        except Exception as e:
            logger.error(f"Error updating live status: {e}")
            return False

    def clean_nolive(self, nolivelist):
        """Remove channels that are not live from the database."""
        if not nolivelist:
            return
        self.live_db.live.delete_many({"channel": {"$in": nolivelist}})

    def search_channels(self, query, limit=50, skip=0):
        """Search for channels by text query."""
        return list(self.db.channel.find({"$text": {"$search": query}}).skip(skip).limit(limit))

    def search_videos(self, query, limit=50, skip=0):
        """Search for videos by text query."""
        return list(self.db.videos.find({"$text": {"$search": query}}).skip(skip).limit(limit))

    def get_collaborations(self, channel_id, limit=50, skip=0):
        """Get videos where the specified channel is a collaborator."""
        return list(
            self.db.videos.find({"collaborators.channel_id": channel_id}).skip(skip).limit(limit)
        )

    def upgrade_channel_data_format(self):
        """
        升級舊的頻道資料格式到新格式
        將缺少的必要欄位添加到現有記錄中
        """
        try:
            logger.info("開始升級頻道資料格式...")

            # 獲取所有頻道記錄
            all_channels = list(self.db.channel.find())
            updated_count = 0

            for channel in all_channels:
                update_data = {}
                needs_update = False

                # 檢查並添加缺少的必要欄位
                required_fields = {
                    "name": "",
                    "company": "",
                    "country": "",
                    "channel_url": "",
                    "platform": "youtube",  # 預設為 youtube
                    "subscriber_count": 0,
                    "view_count": 0,
                    "video_count": 0,
                    "activity_status": "active",
                    "debut_date": "",
                    "thumbnail": "",
                    "channel_id": "",
                }

                # 檢查每個必要欄位
                for field, default_value in required_fields.items():
                    if field not in channel or channel[field] is None:
                        update_data[field] = default_value
                        needs_update = True

                # 特殊處理：如果有 channel_url 但沒有 platform，根據 URL 判斷平台
                if "channel_url" in channel and channel["channel_url"]:
                    if "platform" not in channel or not channel["platform"]:
                        if "youtube.com" in channel["channel_url"]:
                            update_data["platform"] = "youtube"
                        elif "twitch.tv" in channel["channel_url"]:
                            update_data["platform"] = "twitch"
                        else:
                            update_data["platform"] = "unknown"
                        needs_update = True

                # 如果需要更新，執行更新操作
                if needs_update:
                    self.db.channel.update_one({"_id": channel["_id"]}, {"$set": update_data})
                    updated_count += 1
                    logger.debug(
                        f"已更新頻道: {channel.get('name', 'Unknown')} ({channel.get('channel_id', 'No ID')})"
                    )

            logger.info(f"頻道資料格式升級完成，共更新了 {updated_count} 個頻道記錄")
            return updated_count

        except Exception as e:
            logger.error(f"升級頻道資料格式時發生錯誤: {e}")
            return 0

    def migrate_old_channel_format(self, old_format_mapping=None):
        """
        遷移舊格式的頻道資料

        Args:
            old_format_mapping: 舊欄位名稱到新欄位名稱的映射字典
                              例如: {'old_name': 'name', 'old_company': 'company'}
        """
        try:
            if not old_format_mapping:
                # 預設的欄位映射，根據您的實際舊格式調整
                old_format_mapping = {
                    "channel_name": "name",
                    "agency": "company",
                    "region": "country",
                    "url": "channel_url",
                    "service": "platform",
                }

            logger.info("開始遷移舊格式頻道資料...")
            migrated_count = 0

            all_channels = list(self.db.channel.find())

            for channel in all_channels:
                update_data = {}
                needs_update = False

                # 檢查是否有舊格式欄位需要遷移
                for old_field, new_field in old_format_mapping.items():
                    if old_field in channel and new_field not in channel:
                        update_data[new_field] = channel[old_field]
                        needs_update = True

                if needs_update:
                    self.db.channel.update_one({"_id": channel["_id"]}, {"$set": update_data})
                    migrated_count += 1
                    logger.debug(f"已遷移頻道資料: {channel.get('name', 'Unknown')}")

            logger.info(f"舊格式資料遷移完成，共遷移了 {migrated_count} 個頻道記錄")
            return migrated_count

        except Exception as e:
            logger.error(f"遷移舊格式資料時發生錯誤: {e}")
            return 0
