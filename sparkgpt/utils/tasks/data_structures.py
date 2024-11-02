from sortedcontainers import SortedKeyList


def add_comparison_methods(attribute):
    def decorator(cls):
        def gt(self, other):
            return getattr(self, attribute) > getattr(other, attribute)

        def lt(self, other):
            return getattr(self, attribute) < getattr(other, attribute)

        def eq(self, other):
            if (
                isinstance(other, str)
                or isinstance(other, int)
                or isinstance(other, float)
            ):
                return getattr(self, attribute) == other

            return getattr(self, attribute) == getattr(other, attribute)

        def ne(self, other):
            if (
                isinstance(other, str)
                or isinstance(other, int)
                or isinstance(other, float)
            ):
                return getattr(self, attribute) != other

            return getattr(self, attribute) != getattr(other, attribute)

        cls.__ne__ = ne
        cls.__gt__ = gt
        cls.__lt__ = lt
        cls.__eq__ = eq
        return cls

    return decorator


class SortedObjList(SortedKeyList):
    def __init__(self, iterable=None, key=lambda x: x):
        super().__init__(iterable, key=key)

    def find_by_obj(self, match_key):
        i = self.bisect_left(match_key)
        return self[i] if i < len(self) and self[i] == match_key else None

    def find(self, value):
        i = self.bisect_key_left(value)
        if i < len(self) and self._key(self[i]) == value:
            return self[i]
        return None

    def find_n_set(self, value, attrs: list, values: list):
        obj = self.find(value)
        if obj:
            for attr, value in zip(attrs, values):
                setattr(obj, attr, value)
        return obj
