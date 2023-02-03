from getvideolist import getlist
from videoanalyzer import analyze
import time
import pprint
class taskclass():
    def __init__(self,url):
        self.url = url
        self.videolist = getlist(url)
        self.starttime = time.time()
        self.videos = len(self.videolist)
        self.process = 0
        self.maxprocess = self.videos
        self.videosinfo = []


    def run(self):
        for i in self.videolist:
            self.videosinfo = analyze(i).getdata()
            # do something with self.vinfo
            # ...





            
            self.process += 1





    
class taskmanger():
    def __init__(self) -> None:
        self.tasks = []
        self.status = 'idle'
        self.where = None
        self.starting_boot()

    # 初始化
    def starting_boot(self):
        self.status = 'booting'
        self.where = 'starting_boot'
        # get list form mongodb and update all data
        test = "UCdn5BQ06XqgXoAxIhbqw5Rg"
        # vdlist = getlist(test)
        # analyzed = analyze(vdlist[0])
        analyzed = analyze("https://www.youtube.com/watch?v=K0WBLODVfy8").getdata()
        print(analyzed)

    
    # 主迴圈
    def main(self):
        ...
        # 檢查是否有新任務
        # 如果有: 執行新任務
        # 如果沒有: 同步資料到mongodb
        ...
    # 開始任務
    def run_task(self):
        ...
    # return 目前爬蟲位置
    def get_where(self):
        return self.where
    # return 目前爬蟲狀態
    def get_status(self):
        return self.status
    # 添加任務
    def add_task(self):
        ...
    # 同步資料到mongodb
    def syncdata(self):
        ...

if __name__ == "__main__":
    taskmanger()