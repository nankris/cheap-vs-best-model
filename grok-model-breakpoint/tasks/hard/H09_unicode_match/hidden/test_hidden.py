from match import matches

def test_sharp_s_casefold():
    assert matches("straße", "the STRASSE opens at nine") is True

def test_hyphen_is_one_token():
    assert matches("state", "state-of-the-art design") is False
    assert matches("state-of-the-art", "This is state-of-the-art.") is True

def test_edge_punctuation_and_order():
    assert matches("hello", "well, hello, world") is True
    assert matches("world hello", "hello world") is True
    assert matches("missing", "hello world") is False
