import api
from control import ServiceManager
import threading
import atexit
import signal
import sys
import logging
import coloredlogs

all_threading = []
FORMAT = "[ETERNAL] %(asctime)s %(levelname)s: %(message)s"
logger = logging.getLogger("eternal")
coloredlogs.install(level="INFO")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("eternal.log", encoding="utf-8")
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)


def main():
    somm = threading.Thread(
        target=lambda: api.start().run(
            host="0.0.0.0", port=7600, debug=True, use_reloader=False
        )
    ).start()
    all_threading.append(somm)
    sm = threading.Thread(target=ServiceManager).start()
    all_threading.append(sm)
    logger.info(all_threading)


if __name__ == "__main__":

    def onexit():
        for t in all_threading:
            t.join()

    atexit.register(onexit)

    def signal_handler(signal, frame):
        logger.info("You pressed Ctrl+C!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    main()
