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
        self._session = sessionmaker(bind=engine)

    @classmethod
    def instance(cls):
        '''singleton of database'''
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

    def get_session(self):
        return self._session()

    def init_db(self):
        ''' create schema '''
        session = self.get_session()
        session.execute('''
            CREATE TABLE news(
                id INTEGER PRIMARY KEY,
                title TEXT,
                link TEXT,
                body TEXT,
                date TEXT,
                author TEXT,
                sha1 VARCHAR(100)
                );''')
