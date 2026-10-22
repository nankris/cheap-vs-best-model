import unicodedata

_EDGES = ".,;:!?" + "'" + '"' + "`()[]{}"

def normalize_token(token):
    stripped = token.strip(_EDGES)
    return unicodedata.normalize("NFC", stripped.casefold())
