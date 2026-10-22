from reader import load

def test_v1_ada():
    got = load({"full_name": "Ada", "age": "36", "city": "London"})
    assert got["name"] == "Ada"
    assert got["age"] == 36
    assert got["city"] == "London"
    assert got["version"] == 2
    assert "full_name" not in got
