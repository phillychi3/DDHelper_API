import argparse
import logging
import os
import signal
import threading
import time

# Force IPv4
import urllib3.util.connection

urllib3.util.connection.HAS_IPV6 = False


import coloredlogs
import yaml

import api
from controller import VtuberTrackerControl
from database_schema import VtuberDatabase


API_ONLY_MODE = True


nowpath = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(nowpath, "config.yaml"), encoding="utf-8") as f:
    setting = yaml.load(f, Loader=yaml.FullLoader)


DEV_MODE = setting.get("dev_mode", False)

db = VtuberDatabase(setting["database"])
db.reset_live()

api.init_api(db, dev_mode=DEV_MODE)


FORMAT = "[VtuberTracker] %(asctime)s %(levelname)s: %(message)s"
logger = logging.getLogger("vtuber_tracker")
if DEV_MODE:
    coloredlogs.install(level="DEBUG")
    logger.setLevel(logging.DEBUG)
else:
    coloredlogs.install(level="INFO")
    logger.setLevel(logging.INFO)
handler = logging.FileHandler("vtuber_tracker.log", encoding="utf-8")
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)


all_threading = []


def init_api_thread(tracker_control=None):
    api_thread = threading.Thread(
        target=lambda: api.start(
            host=setting.get("api_host", "0.0.0.0"),
            port=setting.get("api_port", 7600),
            debug=DEV_MODE,
        ),
        name="API_Thread",
    )
    api_thread.daemon = True
    api_thread.start()
    all_threading.append(api_thread)
    return api_thread


def init_tracker_thread():
    tracker_control = VtuberTrackerControl(db, setting["youtube_api_key"], DEV_MODE)
    tracker_control.max_api_units_per_day = setting.get("max_api_units_per_day", 10000)

    if not setting.get("youtube_api_key") or setting.get("disable_api", False):
        tracker_control.api_quota_exceeded = True
        logger.info("API usage disabled by configuration")

    api.init_api(db, tracker_control, dev_mode=DEV_MODE)

    tracker_thread = threading.Thread(target=tracker_control.start, name="Tracker_Thread")
    tracker_thread.daemon = True
    tracker_thread.start()
    all_threading.append(tracker_thread)
    return tracker_thread, tracker_control


def main(api_only=False):
    """Main entry point.

    Args:
        api_only: If True, only start API server without tracker controller
    """
    if api_only:
        logger.info("Starting in API-only mode (tracker disabled)")
        init_api_thread()
    else:
        logger.info("Starting in full mode (API + tracker)")
        init_api_thread()
        init_tracker_thread()

    try:
        while all_threading:
            for t in all_threading[:]:
                if not t.is_alive():
                    logger.error(f"Thread {t.name} is dead, restarting...")
                    all_threading.remove(t)
                    if "API_Thread" == t.name:
                        init_api_thread()
                        logger.info("API is restarted")
                    elif "Tracker_Thread" == t.name and not api_only:
                        init_tracker_thread()
                        logger.info("Tracker is restarted")

            if not all_threading:
                logger.error("All threads are dead, exiting...")
                break

            time.sleep(1)
    except Exception as e:
        logger.error(f"??? main thread error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VTuber Tracker Service")
    parser.add_argument(
        "-a",
        "--api-only",
        action="store_true",
        help="Run in API-only mode (disable tracker controller)",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    args = parser.parse_args()

    if args.debug:
        DEV_MODE = True
        coloredlogs.install(level="DEBUG")
        logger.setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")

    api_only_mode = args.api_only or setting.get("api_only_mode", False)

    def signal_handler(signal, frame):
        logger.info("Received SIGINT, shutting down")
        print("exit")
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    main(api_only=api_only_mode)
