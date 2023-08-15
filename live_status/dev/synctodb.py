import json
import sys
sys.path.insert(0, '.')
from database import mongodata
db = mongodata("")
path = input("enter path")

with open(path, 'r') as f:
    data = json.load(f)

for i in data:
    dd = data[i]
    db.insert_channel({
        "name": dd["name"],
        "company": dd["company"],
        "country": dd["country"],
        "channel_url": dd["url"],
        "platform": dd["platform"],
    })