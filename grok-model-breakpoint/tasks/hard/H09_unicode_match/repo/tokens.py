from normalize import normalize_token

def tokenize(text):
    return [normalize_token(part) for part in text.split() if part]
