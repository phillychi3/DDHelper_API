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
            channel_id = channel_data.get("channel_id")
            if not channel_id:
                logger.error("Cannot insert channel without channel_id")
                return False

            self.db.channel.update_one(
                {"channel_id": channel_id}, {"$set": channel_data}, upsert=True
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

            self.db.videos.update_one(
                {"video_id": video_id}, {"$set": video_data}, upsert=True
            )
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
        return list(
            self.db.channel.find({"$text": {"$search": query}}).skip(skip).limit(limit)
        )

    def search_videos(self, query, limit=50, skip=0):
        """Search for videos by text query."""
        return list(
            self.db.videos.find({"$text": {"$search": query}}).skip(skip).limit(limit)
        )

    def get_collaborations(self, channel_id, limit=50, skip=0):
        """Get videos where the specified channel is a collaborator."""
        return list(
            self.db.videos.find({"collaborators.channel_id": channel_id})
            .skip(skip)
            .limit(limit)
        )
