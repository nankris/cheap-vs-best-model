from match import matches

def test_composed_and_decomposed_cafe():
    assert matches("café", "Cafe\u0301 menu") is True
