#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
from utils import re_compile  # copy from web.utils, in memory of Aaron Swartz
import os
import json
import tornado.web
import tornado.wsgi
import tornado.httpserver
import tornado.httpclient
import tornado.options
import logging
import db
from hashlib import sha1
from models import *
from sqlalchemy import func
from sqlalchemy import or_, and_
import datetime
#from tornado.options import define, options
#define("port", default=8888, help="run on the given port", type=int)


class BaseHandler(tornado.web.RequestHandler):
    def search(self, kw_list):
        ''' simple key word searching, using sql LIKE'''
        logging.debug("searching, keywords = %s" % kw_list)
        condition = and_(*[New.search_text.like('%'+word.encode("utf-8")+'%')
                         for word in kw_list])
        res = New.query.filter(condition)
        return res


class IndexHandler(BaseHandler):
    ''' render news list'''
    def get(self):
        news = New.query.order_by('id desc')
        self.render("index.html", news=news)


class LatestHandler(BaseHandler):
    def get(self, format='json'):
        '''
        newest id, sha1, title, link
        /latest
        '''
        max_id = db.ses.query(func.max(New.id)).one()[0]
        new = New.query.filter(New.id == max_id).one()
        self.write(new.to_json())


class IdRegionHandler(BaseHandler):
    def get(self, id1, id2, format='json'):
        ''' get news from id1 to id2
        e.g.
        /id/2000-2003
        '''
        ls = New.query.filter(New.id >= id1, New.id <= id2).order_by('id desc')
        res = [new.to_dict(body=True) for new in ls]
        self.write(json.dumps(res))


class DateRegionHandler(BaseHandler):
    def get(self, date1, date2):
        '''
        e.g.
        /date/2013-2-15/2013-3-2
        '''
        d1 = datetime.date(*[int(x) for x in date1.split('-')])
        d2 = datetime.date(*[int(x) for x in date2.split('-')])
        q = New.query.filter(New.date >= d1, New.date <= d2)
        news = q.order_by('id desc')  # order by id


class QueryById(BaseHandler):
    def get(self, id):
        '''
        e.g.
        /id/2003
        '''
        try:
            new = New.query.filter(New.id == id).one()
            self.write(new.to_json(body=True))
        except:
            self.write("")


class QueryByDate(BaseHandler):
    def get(self, date_str):
        '''
        e.g.
        /date/2013-3-1
        '''
        logging.debug('query date string = %r' % date_str)
        date = datetime.date(*[int(x) for x in date_str.split('-')])
        news = New.query.filter(New.date == date)
        news_dict = [new.to_dict(body=True) for new in news]
        self.write(json.dumps(news_dict))


class SearchHandler(BaseHandler):
    # TODO keyword search engine
    def get(self, keywords=None):
        kw_list = keywords.split(' ')
        res = self.search(kw_list)
        result = [r.to_dict(body=True) for r in res]
        self.write(json.dumps(result))


class TestSearchHandler(BaseHandler):
    def post(self):
        kw_list = self.get_argument('kw_list')
        res = self.search(kw_list.split(' '))
        logging.debug("search ended, begin reder page")
        self.render('search_result.html',
                    res=res, kw_list=kw_list.split(' '))

settings = {
    "debug": True,
    "static_path": os.path.join(os.path.dirname(__file__), 'static'),
    "template_path": os.path.join(os.path.dirname(__file__), 'templates'),
    "cookie_secret": "61eJJFuYh7EQnp2XdTP1o/VooETzKXQAGaYdkL5gEmG=",
}

application = tornado.web.Application([
    (r'/$', IndexHandler),
    (r'/test/search/', TestSearchHandler),

    (r'/latest$', LatestHandler),

    (r'/id/(\d+)$', QueryById),
    (r'/id/(\d+)-(\d+)', IdRegionHandler),

    (r'/date/(\d{4}-\d{1,2}-\d{1,2})$', QueryByDate),
    (r'/date/(\d{4}-\d{1,2}-\d{1,2})/(\d{4}-\d{1,2}-\d{1,2})$',
        DateRegionHandler),

    (r'/search/(.+)', SearchHandler),
    (r'/search', SearchHandler),  # for post

    (r'/static/(.*)',
        tornado.web.StaticFileHandler,
        dict(path=settings['static_path'])),
], **settings)


def main():
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(getattr(sys, 'PORT', 8000))

    tornado.options.parse_command_line(sys.argv)

    if settings['debug']:  # if debug on, change logging level
        logging.getLogger().setLevel(logging.DEBUG)

    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
