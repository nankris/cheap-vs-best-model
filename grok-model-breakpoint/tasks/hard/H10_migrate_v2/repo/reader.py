from migrate import to_v2

def load(record):
    return to_v2(record)
