from ytlv import islive
import json
import random
import time
import asyncio
lv=islive()


def Live_spider(url):
    if "youtube.com" in url:
        live = lv.ytlk(str(url))