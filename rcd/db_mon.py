import oracledb
import logging
from datetime import datetime
from rcd.config import settings
from rcd.config.log_config import setup_logging
import time

log = logging.getLogger(__name__)

db_config = settings[settings.db_name]

dsn = db_config.oracle.dsn
username = db_config.admin.user
password = db_config.admin.password

query = f"""
SELECT 
    SUM(bytes)/1024/1024 AS "Size_MB" 
FROM 
    dba_segments 
WHERE 
    owner = '{settings.db.user}'
"""

def get_db_size():
    try:
        with oracledb.connect(user=username, password=password, dsn=dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                size_mb = cursor.fetchone()[0]
                return size_mb
    except oracledb.Error as e:
        logging.error(f"Database error: {e}")

def main():    
    while True:
        db_size = get_db_size()
        if db_size is not None:
            
            log.info(f'{db_size}')
        time.sleep(900)

if __name__ == "__main__":
    setup_logging()
    main()
