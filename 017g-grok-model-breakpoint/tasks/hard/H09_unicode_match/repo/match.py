from tokens import tokenize

def matches(query, text):
    wanted = tokenize(query)
    have = tokenize(text)
    return all(token in have for token in wanted)
