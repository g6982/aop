#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import functools


# 认证
def validate_user_password(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        return func(*args, **kwargs)
    return wrap
