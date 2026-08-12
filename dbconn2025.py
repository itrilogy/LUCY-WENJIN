# -*- coding: utf-8 -*-
"""SQLite 连接封装（兼容爬虫旧接口，内部走 core.db）。"""

from __future__ import annotations

from typing import Any, Sequence

from core.db import execute, get_conn, query_tuples


class DBConn:
    """单例外观：与历史代码 API 兼容。"""

    _initialized = False

    def __init__(self):
        self.conn = get_conn()
        DBConn._initialized = True

    def execSql(self, sqlstr: str, params: Sequence[Any] = ()):
        execute(sqlstr, params)

    def execQuery(self, sqlstr: str, params: Sequence[Any] = ()):
        return query_tuples(sqlstr, params)
