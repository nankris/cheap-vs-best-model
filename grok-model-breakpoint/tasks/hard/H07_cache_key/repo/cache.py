class Cache:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        self._data[key] = value

    def drop_user(self, user):
        # Drops an entry only when the key is exactly the user id.
        self._data.pop(user, None)

    def clear(self):
        self._data.clear()
