from weeks import week_key

def sum_by_week(rows):
    totals = {}
    for iso_date, amount in rows:
        key = week_key(iso_date)
        totals[key] = totals.get(key, 0) + amount
    return totals
