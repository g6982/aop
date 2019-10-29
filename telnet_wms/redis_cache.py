#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import redis


def get_redis_client(db):
    '''
    :param db: 数据库
    :return:
    '''
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True, db=db)
    return redis_client
