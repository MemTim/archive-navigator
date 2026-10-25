# -*- coding: utf-8 -*-
"""Записи избранного: путь и необязательное пользовательское название."""
from .imports import *  # noqa: F401,F403
from . import vfs


def path(value):
    if isinstance(value, dict):
        return value.get('path') or ''
    return value or ''


def name(value):
    p = path(value)
    if isinstance(value, dict):
        n = str(value.get('name') or '').strip()
        if n:
            return n
    return vfs.basename(p.rstrip('/')) or p or '?'


def make(path, name=''):
    p = path or ''
    n = str(name or '').strip()
    if p and n and n != (vfs.basename(p.rstrip('/')) or p):
        return {'path': p, 'name': n}
    return p
