import requests
import json
import logging

def getlist(url):
    nextpage = ""
    allvideo = []
    while 1:
        apiurl = f"https://www.googleapis.com/youtube/v3/search?key=REMOVED&channelId={url}&part=snippet,id&order=date&maxResults=50&pageToken={nextpage}"
        r = requests.get(apiurl)
        jason = r.json()
        try:
            nextpage = jason["nextPageToken"]
        except:
            break
        for i in jason["items"]:
            try:
                print(i['id']['videoId'])
                allvideo.append(f"https://www.youtube.com/watch?v={i['id']['videoId']}")
            except:
                print("ERROR")
    return allvideo
