import hashlib
import time

from django.core.cache import cache
from rest_framework.exceptions import Throttled


def limit(kind, identity, count, seconds=60):
    bucket = int(time.time()) // seconds
    key = "medora:" + hashlib.sha256(f"{kind}:{identity}:{bucket}".encode()).hexdigest()
    cache.add(key, 0, timeout=seconds + 1)
    try:
        hits = cache.incr(key)
    except ValueError:
        cache.add(key, 0, timeout=seconds + 1)
        hits = cache.incr(key)
    if hits > count:
        raise Throttled(wait=seconds - int(time.time()) % seconds)
