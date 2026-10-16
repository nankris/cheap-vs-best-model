from views import get_view, clear, call_count

def test_archived_flag_is_part_of_the_key():
    clear()
    first = get_view("ada", include_archived=False)
    second = get_view("ada", include_archived=True)
    assert first == ["ada:active"]
    assert second == ["ada:active", "ada:archived"]
    assert call_count() == 2
