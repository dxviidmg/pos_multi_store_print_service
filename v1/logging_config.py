import logging
from logging.handlers import RotatingFileHandler

# Configuración del logger
log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Configuración para rotar el log (máximo 1 MB por archivo, hasta 5 archivos de respaldo)
log_handler = RotatingFileHandler("error_log.txt", maxBytes=1_048_576, backupCount=5)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
logger.addHandler(log_handler)
