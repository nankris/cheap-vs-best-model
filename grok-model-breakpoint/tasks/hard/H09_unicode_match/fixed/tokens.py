from normalize import normalize_token

def tokenize(text):
    out = []
    for part in str(text).split():
        token = normalize_token(part)
        if token:
            out.append(token)
    return out
