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
import datetime
#from tornado.options import define, options
#define("port", default=8888, help="run on the given port", type=int)


class BaseHandler(tornado.web.RequestHandler):
    ''' Basehandler, along with wrapper methods for manipulate news table
    '''
    def store_news(self, id, title, link, date, author, isread=0, body=''):
        '''store news into database.
        id should be assigned by the author
        the newer the new is the bigger the id is
        '''
        #title = unicode(title, 'utf-8')
        #link = unicode(link, 'utf-8')
        #author = unicode(author, 'utf-8')
        #body = unicode(body, 'utf-8')

        full_str = ''.join([title, link, date, author, body])
        full_str = full_str.encode('utf-8')
        logging.debug("full_str = %r" % full_str)
        hashed = sha1(full_str).hexdigest()

        if isinstance(date, str):
            date = datetime.date(*[int(v) for v in date.split('-')])
            # ugly code above , FIXME later
        new = New(
            id=id,
            title=title,
            link=link,
            date=date,
            author=author,
            body=body,
            sha1=hashed)
        logging.debug("new = %r" % new)
        db.ses.add(new)
        db.ses.commit()

    def query_news(self, oldest=0, latest=0):
        ''' Query news which in the date interval (oldest, latest).
        '''
        if latest == 0:
            res = New.query.filter(New.id > oldest)
        elif oldest == 0:
            res = New.query.filter(New.id < latest)
        else:
            res = New.query.filter(New.id > oldest, New.id < latest)
        return res

    def get_news_seq(self):
        res = db.ses.query(New.id).order_by(New.id.desc())
        return [r.id for r in res]

    def query(self, id):
        return New.query.filter(New.id == id).first()


class TestHandler(BaseHandler):
    ''' render news list'''
    def get(self):
        self.render("index.html")

settings = {
    "debug": True,
    "static_path": os.path.join(os.path.dirname(__file__), 'static'),
    "template_path": os.path.join(os.path.dirname(__file__), 'templates'),
    "cookie_secret": "61eJJFuYh7EQnp2XdTP1o/VooETzKXQAGaYdkL5gEmG=",
}

application = tornado.web.Application([
    #(r"/get-oldest=([\d]+)-latest=([\d]+)-t=(\d+)", GetNewsHandler),
    #(r"/update", UpdateHandler),
    #(r"/getcontent/(\d+)", ContentGetHandler),
    (r'/$', TestHandler),
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
