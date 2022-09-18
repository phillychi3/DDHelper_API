from getvideolist import getlist
from videoanalyzer import analyze



class taskmanger():
    def __init__(self) -> None:
        self.tasks = []
        self.status = 'idle'
        self.where = None
        self.starting_boot()


    def starting_boot(self):
        self.status = 'booting'
        self.where = 'starting_boot'
        # get list form mongodb and update all data
        test = "UCdn5BQ06XqgXoAxIhbqw5Rg"
        vdlist = getlist(test)
        analyzed = analyze(vdlist[0])
        print(analyzed)

    def run_task():
        ...

    def get_where():
        ...

    def get_status():
        ...
    def add_task():
        ...


if __name__ == "__main__":
    taskmanger()