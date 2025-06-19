# schedule_job.py
from crontab import CronTab
cron = CronTab(user=True)
job = cron.new(command='python3 /path/to/main.py >> /path/to/stb.log 2>&1', comment="STB warrant hedge")
job.setall('0 18 * * 1-5')  # chạy lúc 18:00 các ngày thứ 2–6
cron.write()
print("Cron job created:", job)
