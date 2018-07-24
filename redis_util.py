# -*- coding: utf-8 -*-

import redis

from config import ConfigRedis


_pool = redis.ConnectionPool(host=ConfigRedis.host, port=ConfigRedis.port)


def get_redis():
    return redis.Redis(connection_pool=_pool, db=ConfigRedis.db)
