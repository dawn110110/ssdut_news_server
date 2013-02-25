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

SSDUT_SITE = "http://ssdut.dlut.edu.cn"


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

# TODO all the below code should be changed


class UpdateHandler(BaseHandler):
    '''Update the news from ssdut web site and store them in database.

    It will check the latest news first. if there is one or more news not in
    database, UpdateHandler will automatically download and store it in
    database. If the latest news has in the database, UpdateHandler will find
    the nearest 'hole' in the database and try to fix it.
    '''

    news_cache = None
    #has_init = False

    #@tornado.web.asynchronous
    def post(self):
        self.update(1, True)

    def get(self):
        self.update(1, True)
        self.write("yes!")

    def update(self, page, ongoing=False, callback=None):
        '''Update the news in 'page' to database.

        If ongoing is True, when it finish update the news from page number
        'page', it will automatically update the news from other page to fix
        the hole in database or try to fetch all news in the website. But this
        will happen only once in one call.
        'callback' for the function to call back. it wwill be sent a param
        indicate wether update success. If success sent True, else False.
        If 'ongoing' is True, callback will only called once in the first time
        when 'update' finish.
        '''

        def _on_download(response):
            '''Called when the page has been catched'''
            logging.debug("_on_download, %r" % response.code)

            if response.code == 200:
                raw_result, entries_num, total_page =\
                    self._decode(response.body)  # decode

                logging.debug("%r" % response.request.url)

                curr_page = int(re.search(r'/p/(\d+)',
                                response.request.url).group(1))
                result = self._encode(raw_result, entries_num, curr_page)

                for i in result:
                    logging.debug("%r" % i)

                max_no = max([x["no"] for x in result])
                min_no = min([x["no"] for x in result])

                # if not stored , store it
                oldest = (min_no-1)
                latest = (max_no+1)
                logging.debug("oldest=%r, latest=%r" % (oldest, latest))
                entries = self.query_news(oldest, latest)

                for ret in result:
                    for entry in entries:
                        if ret["no"] == entry["no"]:
                            break
                    else:
                        logging.debug("no break")
                        # NOTE hack
                        ret['id'] = ret['no']
                        del ret['no']
                        logging.debug("%r" % ret)
                        self.store_news(**ret)

                if ongoing:
                    # fix the hole and try catch whole
                    seq = self.get_news_seq()
                    hole = self._search_hole(seq)
                    logging.debug("hole, %r" % hole)
                    if hole >= min(seq):
                        page = (entries_num - hole)/12+1
                        logging.debug("page, %r" % page)
                        self.update(page, False)
                    else:
                        logging.debug("in last, %r, %r" % (entries_num,
                                                           min(seq)))
                        page = (entries_num-min(seq)+1)/12+1
                        logging.debug("last")
                        self.update(page, False)
                    #if self.request.connection.stream.closed():
                        #return
                    #self.finish()
                if callback is not None:
                    callback(True)
            else:
                if callback is not None:
                    callback(False)

        logging.debug("Before update")
        http = tornado.httpclient.AsyncHTTPClient()
        http.fetch(SSDUT_SITE+"/index.php/News/student/p/%d" % page,
                   _on_download)
        logging.debug("After update")

    def _search_hole(self, nums):
        '''Find the first hole of an sorted natrual array'''
        gap = len(nums)
        if gap == 0:
            return 0
        start = 0
        end = gap - 1
        # In order to unify the calculate, all index start with 1
        logging.debug("Search hole")
        while(gap != 2):
            if nums[start] - gap/2 != nums[start+gap/2]:
                # if left part has a hole
                end = start + gap/2
                gap = end-start+1
                continue
            # else in the right part there is a hole
            if gap % 2 == 0:
                #print "DEBUG", nums[end] + gap/2 - 1 , nums[end-gap/2+1]
                if nums[end] + gap/2 - 1 != nums[end-gap/2+1]:
                    # if left part has a hole
                    start = end-gap/2+1
                    gap = end-start+1
                    continue
            else:
                if nums[end] + gap/2 != nums[end-gap/2]:
                    # if left part has a hole
                    start = end-gap/2
                    gap = end-start+1
                    continue
            ret = min(nums)-1
            logging.debug("Search hole, return last %r" % ret)
            return ret

        if nums[start]-1 != nums[end]:
            logging.debug("Search hole, return hole %r" % nums[start]-1)
            return nums[start]-1

    def _decode(self, content):
        '''Decode the news from ssdut's web page.
        Return as (result, records, page)
        '''
        news_pattern = re_compile(
            r'<tr\ bgcolor=#EEEEEE>[\s\S]+?' +
            r'<td height="24" align="center">(\d+?)</td>' +  # seq
            r'[\s\S]+?href="(.+?)"[\s\S]+?>' +               # link
            r'(.+?)</a>[\s\S]+?' +                           # title
            r'"center">(.+?)</td>' +                         # date
            r'[\s\S]+?<a.+?>(.+?)</a>' +                     # author
            r'[\s\S]+?</tr>')

        result = news_pattern.findall(content)
        entries, page = self._get_page_num(content)
        return (result, entries, page)

    def _get_page_num(self, content):
        '''get the number of total pages and return (record num, page num)'''
        page_debug_pattern = re_compile(
            r'<td width="80%">' +
            r'<font color="#666666">共(\d+?) 条记录/(\d+?)页')
        result = page_debug_pattern.search(content)

        return (int(result.group(1)), int(result.group(2)))

    def _encode(self, content, total_entry, curr_page):
        '''Encode it into object formatter like:

            [{
                no:2122
              link:"index.htm",
             title:"News"
              date:"2012-4-8"
            author:"Jim"
            isread:0
            },
            {entry 2},
            ...
            {entry n},
            ]
            Every time it will send only one page i.e. no more than 12 entries
            '''

        result = []
        for entry in content:
            d = {}
            d["no"] = total_entry - 12*(curr_page-1) - (int(entry[0])-1)
            d["link"] = entry[1]
            d["title"] = entry[2]
            d["date"] = entry[3]
            d["author"] = entry[4]
            result.append(d)
        return result


class GetNewsHandler(UpdateHandler):
    '''Get news from database

    Before it return method get will check if there is a hole before the
    'last_news_no'. If there is it will update the hole first then return
    there result.
    '''

    @tornado.web.asynchronous
    def get(self, oldest, latest, time):
        '''Return the news which's number after last_news_no(i.e. newer)'''
        self.oldest = oldest
        self.latest = latest
        seq = self.get_news_seq()
        hole = self._search_hole(seq)
        if int(oldest) != 0:
            if hole < oldest:
                self.get_news(int(oldest), int(latest))
                self.finish()
            else:
                logging.debug("get for update")
                self.get_news(hole, int(latest))
                self.update(1, True, self.on_update)
        else:
            self.get_news(int(oldest), int(latest))
            self.finish()

    def get_news(self, oldest, latest):
        logging.debug("get_news(oldest=%r,latest=%r)" % (oldest, latest))
        result = json.dumps(self.query_news(oldest=oldest, latest=latest))
        self.write(result)

    def on_update(self, success):
        logging.debug("on_update(success=%r)" % success)
        if success:
            self.get_news(int(self.oldest), int(self.latest))
        else:
            self.set_status(404)
            self.write("")

        if self.request.connection.stream.closed():
            return
        self.finish()


class ContentGetHandler(BaseHandler):
    '''Greb the content of this news from ssdut site'''

    def _on_download(self, response):
        logging.debug("_on_download() called")
        if response.code == 200:
            pattern = re_compile(
                r'<td height="36" align="center" class="title">' +
                r'(.+?)</td>[\s\S]+?' +
                r'<td class="content">([\s\S]+)</td>[\s\S]+?' +
                r'<table width="760" border="0" align="center" ' +
                r'cellpadding="0" cellspacing="0" bgcolor="#FFFFFF">')
            result = {}
            result['title'], result['content'] =\
                pattern.search(response.body).group(1, 2)

            self.write(json.dumps(result))
            self.finish()
        else:
            self.set_status(504)
            self.finish()

    @tornado.web.asynchronous
    def get(self, news_id):
        link = self.query(int(news_id))
        if link is not None:
            link = link[2]
        else:
            self.set_status(404)
            self.finish()
        http = tornado.httpclient.AsyncHTTPClient()
        http.fetch(SSDUT_SITE+link, self._on_download)

settings = {
    "debug": True,
}

application = tornado.web.Application([
    (r"/get-oldest=([\d]+)-latest=([\d]+)-t=(\d+)", GetNewsHandler),
    (r"/update", UpdateHandler),
    (r"/getcontent/(\d+)", ContentGetHandler),
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
