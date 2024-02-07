import threading
import signal
import logging
import coloredlogs
import yaml
from database import _init
import os
nowpath = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(nowpath,"ddhelper_live.yaml") ,"r", encoding="utf-8") as f:
    setting = yaml.load(f, Loader=yaml.FullLoader)
_init(setting["database"])
from control import Live_spider_control  # noqa: E402
import api # noqa: E402

DEBUG = False


all_threading = []
FORMAT = "[ddhelper_live] %(asctime)s %(levelname)s: %(message)s"
logger = logging.getLogger("ddhelper_live")
if DEBUG:
    coloredlogs.install(level="DEBUG")
    logger.setLevel(logging.DEBUG)
else:
    coloredlogs.install(level="INFO")
    logger.setLevel(logging.INFO)
handler = logging.FileHandler("ddhelper_live.log", encoding="utf-8")
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)



def main():

    somm = threading.Thread(
        target=lambda: api.start().run(
            host="0.0.0.0", port=7600, debug=DEBUG, use_reloader=False
        )
    )
    somm.daemon = True
    somm.start()
    all_threading.append(somm)
    sm = threading.Thread(target=Live_spider_control,args=(DEBUG,))
    sm.daemon = True
    sm.start()
    all_threading.append(sm)
    try:
        while all_threading:
            for t in all_threading:
                if not t.is_alive():
                    all_threading.remove(t)

    except:
        pass


if __name__ == "__main__":
    def signal_handler(signal, frame):
        logger.info("You pressed Ctrl+C!")

        print("exit")
        os._exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    main()


