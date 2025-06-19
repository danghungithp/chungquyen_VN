# runner.py
import schedule, time
from main import main

schedule.every().day.at("18:00").do(main)

while True:
    schedule.run_pending()
    time.sleep(60)
