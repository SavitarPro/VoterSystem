
from flask import current_app
import psycopg2
import logging
from logging.handlers import RotatingFileHandler
import os
from config import config



def setup_logging(app):
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=1024 * 1024 * 10,  
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    
    app_logger = logging.getLogger('validity_service')
    app_logger.setLevel(log_level)

    
    app_logger.handlers.clear()

    
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)

    return app_logger


def init_app(app):
    
    app.logger = setup_logging(app)


def get_db_connection():
    
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.VALIDITY_DB
    )


def log_activity(level, message, ip_address):
    
    logger = logging.getLogger('validity_service')
    log_message = f"[IP: {ip_address}] {message}"

    if level == 'INFO':
        logger.info(log_message)
    elif level == 'WARNING':
        logger.warning(log_message)
    elif level == 'ERROR':
        logger.error(log_message)
    elif level == 'DEBUG':
        logger.debug(log_message)
    else:
        logger.info(log_message)