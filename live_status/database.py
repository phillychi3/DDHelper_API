import pymongo
from pymongo.server_api import ServerApi


def _init(dblink):
    global db
    db = mongodata(dblink)


class mongodata:
    def __init__(self, dblink):
        self.client = pymongo.MongoClient(dblink, server_api=ServerApi("1"))
        self.db_init_check()
        self.reset_live()

    def db_init_check(self):
        if "vtuber" not in self.client.list_database_names():
            db = self.client.vtuber
        if "channel" not in self.client.vtuber.list_collection_names():
            db = self.client.vtuber.channel
            db.insert_one({"channel": "test"})
            db.delete_one({"channel": "test"})
        if "live" not in self.client.list_database_names():
            db = self.client.live
        if "live" not in self.client.live.list_collection_names():
            db = self.client.live.live
            db.insert_one({"channel": "test"})
            db.delete_one({"channel": "test"})

    def get_channelurl_list(self):
        db = self.client["vtuber"]["channel"]
        return [i["channel_url"] for i in db.find()]

    def get_channels(self):
        db = self.client["vtuber"]["channel"]
        vtubers = []
        for i in db.find():
            vtubers.append({
                "name": i["name"],
                "company": i["company"],
                "country": i["country"],
                "channel_url": i["channel_url"],
                "platform": i["platform"],
            })
        return vtubers
        
    def insert_channel(self, channel_info):
        """
        "name": "",
        "company": "",
        "country": "",
        "clannel_url": "",
        "platform": "",
        """
        db = self.client["vtuber"]["channel"]
        db.insert_one(channel_info)

    def update_channel(self, channel, data):
        db = self.client["vtuber"]["channel"]
        db.update_one({"name": channel}, {"$set": data})

    def replace_channel(self, channel, data):
        db = self.client["vtuber"]["channel"]
        db.replace_one({"name": channel}, data)
        
    def delete_channel(self, channel):
        db = self.client["vtuber"]["channel"]
        db.delete_one({"name": channel})

    def get_one_channel(self, channel):
        db = self.client["vtuber"]["channel"]
        return db.find_one({"name": channel})

    def reset_live(self):
        db = self.client["live"]["live"]
        db.delete_many({})

    def get_one_live(self, channel):
        db = self.client["live"]["live"]
        return db.find_one({"channel": channel})
    
    def getlivefromstatus(self, status):
        db = self.client["live"]["live"]
        return db.find({"status": status})

    def insert_live(self, live_info):
        db = self.client["live"]["live"]
        db.insert_one(live_info)

    def update_live(self, channel, data):
        db = self.client["live"]["live"]
        if self.get_one_live(channel) == None:
            self.insert_live(data)
        else:
            db.update_one({"channel": channel}, {"$set": data})
