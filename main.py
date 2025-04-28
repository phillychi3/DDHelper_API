import threading
import signal
import logging
import coloredlogs
import yaml
import os
import time
from database_schema import VtuberDatabase
from vtuber_collector import VtuberCollector
import api


DEBUG = False


nowpath = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(nowpath, "config.yaml"), "r", encoding="utf-8") as f:
    setting = yaml.load(f, Loader=yaml.FullLoader)


db = VtuberDatabase(setting["database"])
collector = VtuberCollector(
    api_key=setting["youtube_api_key"],
    max_api_calls_per_day=setting.get("max_api_calls_per_day", 10000),
)


api.init_api(db, collector)


FORMAT = "[VtuberTracker] %(asctime)s %(levelname)s: %(message)s"
logger = logging.getLogger("vtuber_tracker")
if DEBUG:
    coloredlogs.install(level="DEBUG")
    logger.setLevel(logging.DEBUG)
else:
    coloredlogs.install(level="INFO")
    logger.setLevel(logging.INFO)
handler = logging.FileHandler("vtuber_tracker.log", encoding="utf-8")
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)


all_threading = []


from control import VtuberTrackerControl


def main():
    """Main entry point."""
    # Start API server
    api_thread = threading.Thread(
        target=lambda: api.start(
            host=setting.get("api_host", "0.0.0.0"),
            port=setting.get("api_port", 7600),
            debug=DEBUG,
        )
    )
    api_thread.daemon = True
    api_thread.start()
    all_threading.append(api_thread)

    tracker_control = VtuberTrackerControl(db, collector, DEBUG)

    tracker_control.max_api_units_per_day = setting.get("max_api_units_per_day", 10000)

    if not setting.get("youtube_api_key") or setting.get("disable_api", False):
        tracker_control.api_quota_exceeded = True
        collector.api_calls_today = collector.max_api_calls_per_day + 1
        logger.info("API usage disabled by configuration")

    tracker_thread = threading.Thread(target=lambda: tracker_control, args=())
    tracker_thread.daemon = True
    tracker_thread.start()
    all_threading.append(tracker_thread)

    try:
        while all_threading:
            for t in all_threading[:]:
                if not t.is_alive():
                    logger.error(f"Thread {t.name} died, removing from list")
                    all_threading.remove(t)

            if not all_threading:
                logger.error("All threads have died, exiting")
                break

            time.sleep(1)
    except Exception as e:
        logger.error(f"Error in main thread: {e}")


if __name__ == "__main__":

    def signal_handler(signal, frame):
        logger.info("Received SIGINT, shutting down")
        print("exit")
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    main()
