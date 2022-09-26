from getvideolist import getlist
from videoanalyzer import analyze



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
        vdlist = getlist(test)
        analyzed = analyze(vdlist[0])
        print(analyzed)

    
    # 主迴圈
    def main():
        ...
    # 開始任務
    def run_task():
        ...
    # return 目前爬蟲位置
    def get_where():
        ...
    # return 目前爬蟲狀態
    def get_status():
        ...
    # 添加任務
    def add_task():
        ...
    # 同步資料到mongodb
    def syncdata():
        ...

if __name__ == "__main__":
    taskmanger()