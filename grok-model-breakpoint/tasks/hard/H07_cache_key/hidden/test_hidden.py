from views import get_view, clear, call_count, bust

def test_role_is_part_of_the_key_and_hits_are_free():
    clear()
    viewer = get_view("ada", role="viewer")
    admin = get_view("ada", role="admin")
    again = get_view("ada", role="admin")
    assert viewer == ["ada:active"]
    assert admin == ["ada:active", "ada:secret"]
    assert again == ["ada:active", "ada:secret"]
    assert call_count() == 2

def test_bust_one_user_and_keep_the_other():
    clear()
    get_view("ada", include_archived=True, role="admin")
    get_view("bea", include_archived=False)
    assert call_count() == 2
    bust("ada")
    get_view("bea", include_archived=False)
    assert call_count() == 2
    refreshed = get_view("ada", include_archived=True, role="admin")
    assert refreshed == ["ada:active", "ada:archived", "ada:secret"]
    assert call_count() == 3

def test_users_do_not_collide():
    clear()
    assert get_view("ada") == ["ada:active"]
    assert get_view("bea", include_archived=True) == ["bea:active", "bea:archived"]
    assert call_count() == 2
