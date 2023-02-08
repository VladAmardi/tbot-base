from django.core.cache import cache
import json
import hashlib


def _make_key(args, kwargs, typed,
              fast_types=None,
              _tuple=tuple, _type=type, _len=len):
    """Make a cache key from optionally typed positional and keyword arguments

    The key is constructed in a way that is flat as possible rather than
    as a nested structure that would take more memory.

    If there is only a single argument and its data type is known to cache
    its hash value, then that argument is returned without a wrapper. These
    saves space and improves lookup speed.

    """
    # All code below relies on kwargs preserving the order input by the user.
    # Formerly, we sorted() the kwargs before looping.  The new way is *much*
    # faster; however, it means that f(x=1, y=2) will now be treated as a
    # distinct call from f(y=2, x=1) which will be cached separately.
    if fast_types is None:
        fast_types = {int, str}
    key = args
    if kwargs:
        for item in kwargs.items():
            key += item
    if typed:
        key += _tuple(_type(v) for v in args)
        if kwargs:
            key += _tuple(_type(v) for v in kwargs.values())
    elif _len(key) == 1 and _type(key[0]) in fast_types:
        return key[0]
    # return json.dumps(key)
    return hashlib.md5(json.dumps(key).encode()).hexdigest()


def cached(key: str, ttl: int = 0, typed=False):
    def __wrapper_func(_func):
        def _wrapper(*args, **kwargs):
            nonlocal key
            key = key + _make_key(args, kwargs, typed)
            result = cache.get(key)
            if result is None:
                result = _func(*args, **kwargs)
                cache.set(key, result, None if ttl == 0 else ttl)
            return result

        return _wrapper

    return __wrapper_func
