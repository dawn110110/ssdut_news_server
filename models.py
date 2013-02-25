from sqlalchemy import Column, Integer, String, Text, Date
from db import Base

__all__ = ['New']

class New(Base):
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True)
    title = Column(String(300))
    link = Column(String(300))
    body = Column(Text(convert_unicode=True))
    date = Column(Date)
    author = Column(String(300))
    sha1 = Column(String(50))

    def __repr__(self):
        return '<New %s - %s>' % (self.title, self.date)

    def __unicode__(self):
        return self.__repr__()
