class Cache:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        self._data[key] = value

    def drop_user(self, user):
        for key in list(self._data):
            owner = key[0] if isinstance(key, tuple) else key
            if owner == user:
                del self._data[key]

    def clear(self):
        self._data.clear()
