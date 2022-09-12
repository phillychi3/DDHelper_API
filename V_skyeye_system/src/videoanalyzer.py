import requests
import re
import json
req = requests.get('https://www.youtube.com/watch?v=8DrC2RecF0M')


linkdata = re.findall(r'"description":{"runs":(.*?)},"subscribeButton"', req.text)
jss=json.loads(linkdata[0])

