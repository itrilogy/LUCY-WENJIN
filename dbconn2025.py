# -*- coding: utf-8 -*-

import sqlite3


class DBConn :
	"""SQLite 连接封装（单例模式，复用同一连接）"""
	_conn = None
	_initialized = False

	def __init__(self):
		if DBConn._conn is None:
			DBConn._conn = sqlite3.connect("/Users/ic/Project/gaokao2025/gaokao2025.sqlite", timeout=30, check_same_thread=False, isolation_level=None)
			DBConn._conn.execute("PRAGMA journal_mode=WAL")
			DBConn._conn.execute("PRAGMA synchronous=NORMAL")
			DBConn._initialized = True
		self.conn = DBConn._conn

	def execSql(self,sqlstr):
		curs=self.conn.cursor()

		curs.execute(sqlstr)

		self.conn.commit()

		curs.close()

	def execQuery(self,sqlstr):
		curs=self.conn.cursor()
		curs.execute(sqlstr)

		rows=curs.fetchall()

		curs.close()

		return rows


