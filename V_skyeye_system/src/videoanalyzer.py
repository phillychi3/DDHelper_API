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
    #FIXME: 無法取得連動者
    def _analyze_Gearing(self,req):
        linkdata = re.findall(r'"commandMetadata":{"webCommandMetadata":{"url":(.*?),"webPageType":"WEB_PAGE_TYPE_CHANNEL"', req.text)
        links = []
        max = 20
        flag = 0
        for i in linkdata:
            if i.startswith('"/channel/'):
                links.append(i.replace('"','').replace('/channel/',''))
            flag += 1
            if flag >= max:
                break
        links = list(set(links))
        #打連結，辨識是否為連動者或者為雜訊
        # 如果是連動者，名稱會出現在簡介中
        return links
        
        # linkdata = re.findall(r'"description":{"runs":(.*?)},"subscribeButton"', req.text)
        # if linkdata == []:
        #     return None
        # jss=json.loads(linkdata[0])
        # ldata = []
        # for i in jss:
        #     try:
        #         ldata.append({
        #             "channelname": i["text"],
        #             "channelurl": "https://www.youtube.com/"+i['navigationEndpoint']['browseEndpoint']['canonicalBaseUrl']
        #         })
        #     except:
        #         pass
        # return ldata

    # 觀看次數
    #FIXME: 'ViewCount': '�[�ݦ��ơG220,104��'
    def _analyze_ViewCount(self,req):
        linkdata = re.findall(r'"viewCount":{"videoViewCountRenderer":{"viewCount":{"simpleText":"(.*?)"},"', req.text)
        return linkdata[0] if linkdata != [] else None
    # 點讚次數
    #FIXME: 'likecount': '13,445 �H���w'
    def _analyze_likecount(self,req):
        linkdata = re.findall(r'"defaultText":{"accessibility":{"accessibilityData":{"label":"(.*?)"}},', req.text)
        return linkdata[0] if linkdata != [] else None
