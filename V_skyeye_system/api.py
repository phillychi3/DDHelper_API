import logging
from src import *


FORMAT = '[Vskyeye] %(asctime)s %(levelname)s: %(message)s'
logger = logging.getLogger('Vskyeye')
logger.setLevel(logging.INFO)

handler = logging.FileHandler('Vskyeye.log',encoding='utf-8')
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)

hdr = logging.StreamHandler()
hdr.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(hdr)


