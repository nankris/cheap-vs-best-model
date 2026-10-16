from loader import load

def test_nested_port_keeps_siblings():
    got = load({"db": {"port": 5433}})
    assert got["db"] == {"host": "localhost", "port": 5433, "name": "app"}
    assert got["service"] == "billing"
    assert got["debug"] is False
