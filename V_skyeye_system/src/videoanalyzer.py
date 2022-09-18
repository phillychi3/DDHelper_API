import requests
import re
import json





def analyze(vid):
    req = requests.get(vid)
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