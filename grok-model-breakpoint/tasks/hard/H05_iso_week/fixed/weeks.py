from dates import parse_iso

def week_key(iso_date):
    day = parse_iso(iso_date)
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
