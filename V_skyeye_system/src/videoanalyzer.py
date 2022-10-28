import requests
import re
import json



class analyze():
    def __init__(self, vid):
        self.vid = vid



    def getdata(self):
        """
        return:
        {
            "gearing": [],
            "viewcount": "",
            "likecount": ""
        }
        """
        req = requests.get(self.vid)
        return {
            "Gearing": self._analyze_Gearing(req),
            "ViewCount": self._analyze_ViewCount(req),
            "likecount": self._analyze_likecount(req)
        }

# 連動者
    def _analyze_Gearing(self,req):
        
        linkdata = re.findall(r'"description":{"runs":(.*?)},"subscribeButton"', req.text)
        jss=json.loads(linkdata[0])
        ldata = []
        for i in jss:
            try:
                ldata.append({
                    "channelname": i["text"],
                    "channelurl": "https://www.youtube.com/"+i['navigationEndpoint']['browseEndpoint']['canonicalBaseUrl']
                })
            except:
                pass
        return ldata

    # 觀看次數
    def _analyze_ViewCount(self,req):
        linkdata = re.findall(r'"viewCount":{"videoViewCountRenderer":{"viewCount":{"simpleText":"(.*?)"},"', req.text)
        return linkdata[0]
    # 點讚次數
    #TODO
    def _analyze_likecount(self,req):
        linkdata = re.findall(r'"defaultText":{"accessibility":{"accessibilityData":{"label":"(.*?)"}},', req.text)
        return linkdata[0]
