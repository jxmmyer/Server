import psutil
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

#Configuration
CPU_THRESHOLD = 80       # CPU usage threshold in percentage
MEMORY_THRESHOLD = 80    # Memory usage threshold in percentage
DISK_THRESHOLD = 90      # Disk usage threshold in percentage
ALERT_EMAIL = "your-email@example.com"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "your-email@example.com"
SMTP_PASSWORD = "your-email-password"

def send_alert(resource, usage):
    subject = f"Alert: {resource} usage is at {usage}%"
    body = f"{resource} usage has reached {usage}%. Please check the system."
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL

with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, ALERT_EMAIL, msg.as_string())

def check_thresholds():
    cpu_usage = psutil.cpu_percent(interval=1)
    if cpu_usage > CPU_THRESHOLD:
        send_alert("CPU", cpu_usage)
    
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    if memory_usage > MEMORY_THRESHOLD:
        send_alert("Memory", memory_usage)
    
    for partition in psutil.disk_partitions():
        if partition.fstype != '':
            disk_usage = psutil.disk_usage(partition.mountpoint).percent
            if disk_usage > DISK_THRESHOLD:
                send_alert(f"Disk ({partition.mountpoint})", disk_usage)

def main():
    hostname = psutil.users()[0].name
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())

    print(f"System Monitoring Report - {current_time}")
    print(f"Hostname: {hostname}")
    print(f"Uptime: {uptime}")
    print(f"CPU Usage: {psutil.cpu_percent(interval=1)}%")
    print(f"Memory Usage: {psutil.virtual_memory().percent}%")
    print("Disk Usage:")
    for partition in psutil.disk_partitions():
        if partition.fstype != '':
            usage = psutil.disk_usage(partition.mountpoint)
            print(f"  {partition.mountpoint}: {usage.percent}%")
    
    check_thresholds()

if __name__ == "__main__":
    main()