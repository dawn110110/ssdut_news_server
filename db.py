#!/usr/bin/env python
#encoding=utf-8
'''db'''
import sqlite3
import config
from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker
import config

__all__ = ['Backend']


class Backend(object):
    def __init__(self):
        engine = create_engine("sqlite:///news.db")
        self._get_session = sessionmaker(bind=engine, autocommit=True)

    @classmethod
    def instance(cls):
        '''singleton of database'''
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

    def get_session(self):
        '''
        for using with statement, autocommit=True 

        usuage:
        with ses.begin():
            ses.execute(.....)
            # ...
        '''
        ses = self._get_session()
        return ses

    def init_db(self):
        ''' create schema '''
        ses = self.get_session()
        with ses.begin():
            ses.execute('''
                CREATE TABLE news(
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    link TEXT,
                    body TEXT,
                    date TEXT,
                    author TEXT,
                    sha1 VARCHAR(100)
                    );''')
