#def log_progress(message):
   # print(message)

#def run_query(query, conn):
 #   print("run_query called")
print("UTILS MODULE LOADED")
import datetime

import os#  IGNORE --- for log file path handling

BASE_DIR = os.path.dirname(os.path.dirname(__file__))#  IGNORE --- to get project root directory
LOG_FILE = os.path.join(BASE_DIR, "code_log", "pipeline.log")#  IGNORE --- log file path setup (assuming code_file is the directory where main.py is located)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)#  IGNORE --- ensure log directory exists  

def log_progress(message, level="INFO"):#  IGNORE --- enhanced logging function with timestamp and log level
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"

    print(log_message)

    with open(LOG_FILE, "a") as f:
        f.write(log_message + "\n")


def run_query(query, conn):
    try:
        log_progress("run_query called")

        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()

        log_progress("Query executed successfully")

    except Exception as e:
        log_progress(f"Query failed: {str(e)}", level="ERROR")
        raise