import datetime as dt
from dates import parse_iso

def week_key(iso_date):
    day = parse_iso(iso_date)
    since_sunday = (day.weekday() + 1) % 7
    start = day - dt.timedelta(days=since_sunday)
    week = int(start.strftime("%U"))
    return f"{start.year}-W{week:02d}"
