class MagicDict:
    def __init__(self, value=None):
        super().__setattr__('_dict', {})
        super().__setattr__('_value', value)

    def __getattr__(self, attr):
        return self._dict.get(attr, _magic_none)

    def __setattr__(self, attr, val):
        self._dict[attr] = MagicDict(val)

    def put(self, attr):
        self.__setattr__(attr, None)
        return self.__getattr__(attr)

    def __bool__(self):
        return True

    def __call__(self):
        return self._value


class MagicNone:
    def __getattr__(self, attr):
        return self

    def __call__(self):
        return None

    def __bool__(self):
        return False


_magic_none = MagicNone()
