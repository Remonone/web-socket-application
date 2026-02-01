import logging
from config_resolver import resolve_config
from constants import *
from connector import ServerWrapper
import uvicorn


if __name__=="__main__":
    logger = logging.getLogger("service")
    cfg = resolve_config(CONFIG_NAME)
    service = ServerWrapper()
    port = cfg["port"]
    logger.log(0, port)
    uvicorn.run(service.app, host="0.0.0.0", port=port)