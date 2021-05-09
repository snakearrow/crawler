import logging

log = logging.getLogger("Crawler")
formatter = logging.Formatter('%(asctime)s [%(levelname)-5.5s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.setLevel(logging.INFO)
log.addHandler(handler)

