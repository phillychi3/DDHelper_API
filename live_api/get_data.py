from ytlv import *
import json
import random
import time
import threading

def start():
    with open("setting.json","r")as f:
        data=json.load(f)

    for i in data:

        with open("live.json","r", encoding='UTF-8')as ff:
            livedata=json.load(ff)
        try:
            if not str(i) in livedata:
                livedata[i]={}
                livedata[i]["name"]=data[i]["name"]
                livedata[i]["company"]=data[i]["company"]
                livedata[i]["country"]=data[i]["country"]
                livedata[i]["clannel_url"]=data[i]["url"]
                livedata[i]["status"]="NONE"
                livedata[i]["picture"]="NONE"
                livedata[i]["title"]="NONE"
                livedata[i]["link"]="NONE"
                livedata[i]["timestamp"]="NONE"
                livedata[i]["laststreamtime"]="NONE"

                with open('live.json', 'w', encoding='UTF-8') as f:
                    json.dump(livedata, f, ensure_ascii=False, indent=4)

            with open("live.json","r", encoding='UTF-8')as ff:
                livedata=json.load(ff)
            lv=islive()
            live=lv.ytlk(str(data[i]["url"]))
            link=live[0]["link"]
            status=live[0]["status"]
            title=live[0]["title"]
            picture=live[0]["picture"]
            timestamp=live[0]["timestamp"]

            livedata[i]["link"]=link
            livedata[i]["status"]=status
            livedata[i]["title"]=title
            livedata[i]["picture"]=picture
            livedata[i]["timestamp"]=timestamp
            if status=="OK":
                livedata[i]["laststreamtime"]=int(time.time())
            with open('live.json', 'w', encoding='UTF-8') as f:
                json.dump(livedata, f, ensure_ascii=False, indent=4)
            time.sleep(3)
        except:
            print("重大錯誤!!!")


def start_getdata():
    start_time=time.time()
    print(start_time)
    sleep_time=random.randint(300,400)
    print("start")
    threading.Thread(target=start, daemon=True, args=()).start()
    time.sleep(sleep_time)
    end_time=time.time()
    print(end_time)
    live_time=(end_time-start_time)
    print(live_time)
    if live_time<180:
        quit()
    start_getdata()


if __name__ == "__main__":
    
    start_getdata()