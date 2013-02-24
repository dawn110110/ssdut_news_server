#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Introduction:
#
# This is an application used to get latest news of the Software
# School, Dalian University of Technology. It is one of the components of a
# windows gadget which named SSdut News. It use to update news in the
# background. This application use Tornado as its basic framework, which is
# one of Facebook open source technologies.
#
# Liscense:
#
#  Copyright 2012 Feng Yuyao
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License
#
# Usage:
#
# This application is running in the background. so we haven't any GUI
# or command user interface to control this program. The user interface
# of this program is the url like http://localhost:port/[param]. We post/get
# http request to these url to control this server. The param's optional
# value is shown as follows(dont't type [] which is indicate a parameter):
#
#    get-oldest=[oldest_news]-latest=[latest_news]-t=[random]
#                         ---- HTTP GET. Use to get the news which's No in
#                              (oldest_news,latest_news], random is a random
#                              number use to prevent the brower's cache. In
#                              this case, if oldest_news is zero, it
#                              indicate to query all news older than latest.
#                              if latest_news is zero, it indicate to query
#                              all news newer than oldest.
#    close                ---- HTTP POST. Close this application and release
#                              the resource.
#    update               ---- HTTP POST. Update news from ssdut website, it
#                              will fix the discontinuous part in database
#                              and check newest news every time.
#    mark[mark]           ---- HTTP POST. Mark the news which's No is 'mark'
#                              to readed
#    getcontent/[no]      ---- HTTP GET. Get the content of the news which's
#                              no is 'no' And this application will post news
#                              to you in an JSON format by http protocol.

import sys
import re
from utils import re_compile  # copy from web.utils, in memory of Aaron Swartz
import os
import json
import sqlite3
import tornado.web
import tornado.wsgi
import tornado.httpserver
import tornado.httpclient
import tornado.options
import logging

#from tornado.options import define, options

SSDUT_SITE = "http://ssdut.dlut.edu.cn"
#sys.WORK_DIR = "SSDUT_NEWS"

#define("port", default=8888, help="run on the given port", type=int)

#sys.stderr = open("ssdut.log", 'w')  #
#sys.stderr = open(os.path.join(os.environ['LOCALAPPDATA'],
                  #getattr(sys, 'WORK_DIR', "SSDUT_NEWS"),
                  #'ssdutNews.log'), 'w')


class BaseHandler(tornado.web.RequestHandler):
    '''Base handler. contain the api of database. '''

    DATABASE_FILE = 'ssdutNews.db'
    # os.environ['LOCALAPPDATA']+'\\ssdutNews.db'
    __database = None

    @classmethod
    def _database(cls):
        '''use to create a database instance. It's singletan'''
        if not cls.__database:
            cls.__database = sqlite3.connect(cls.DATABASE_FILE)
            cur = cls.__database.cursor()
            try:
                cur.execute('''CREATE TABLE news
                    (
                    no integer primary key,
                    title text,
                    link text,
                    date text,
                    author text,
                    isread integer
                    )''')
            except sqlite3.OperationalError:
                pass
            cls.__database.commit()
            cur.close()
        return cls.__database

    def __getattr__(self, attrname):
        if attrname == "db":
            return BaseHandler._database()
        else:
            raise AttributeError(attrname)

    def store_news(self, no, title, link, date, author, isread=0):
        '''This method is used to store news into database.

        Every entry in the database has five value. They are:
            no                 integer
            title              string
            link               string
            date               string
            author             string
            isread             integer  (0 for no read, 1 for readed)
        The value 'no' need user to assign. It indicates how fresh a news is.
        The 'no' is bigger, the news is newer.
        '''
        cur = self.db.cursor()
        cur.execute('''INSERT INTO news (no, title, link, date, author, isread)
                                 VALUES (%d, "%s", "%s", "%s",  "%s", %d)
                ''' % (no, title, link, date, author, isread))
        self.db.commit()
        cur.close()

    def query_news(self, oldest=0, latest=0):
        ''' Query news which in the date interval (oldest, latest).

        It will return result as a list like:
            [
            {"no":no, "title":title, "link":link, "date":date,
            "author":author, "isread":isread},
            news2,
            news3,
            ...,
            ]
        '''

        cur = self.db.cursor()
        if latest == 0:
            cur.execute('''SELECT * FROM news WHERE no > %d ORDER BY no DESC
                    ''' % oldest)
        elif oldest == 0:
            cur.execute('''SELECT * FROM news WHERE no < %d ORDER BY no DESC
                    ''' % latest)
        else:
            cur.execute('''SELECT * FROM news WHERE no > %d AND no < %d ORDER
                    BY no DESC ''' % (oldest, latest))

        result = []
        for entry in cur:
            d = {}
            d["no"] = entry[0]
            d["title"] = entry[1]
            d["link"] = entry[2]
            d["date"] = entry[3]
            d["author"] = entry[4]
            d["isread"] = entry[5]
            result.append(d)
        cur.close()
        return result

    def get_news_seq(self):
        cur = self.db.cursor()
        cur.execute('''SELECT no FROM news ORDER BY no DESC''')
        ret = [x[0] for x in cur.fetchall()]
        cur.close()
        return ret

    def mark_readed(self, news_no):
        cur = self.db.cursor()
        cur.execute('''UPDATE news SET isread=1 WHERE no=%d''' % news_no)
        self.db.commit()
        cur.close()

    def query(self, num):
        cur = self.db.cursor()
        cur.execute('''SELECT * FROM news WHERE no=%d''' % num)
        ret = cur.fetchone()
        cur.close()
        return ret


class CloseHandler(BaseHandler):
    '''Close the server'''

    def post(self):
        self.db.close()
        tornado.ioloop.IOLoop.instance().stop()
        tornado.ioloop.IOLoop.instance().close()
        logging.debug("close")


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
                entries = self.query_news(oldest=(min_no-1),
                                          latest=(max_no+1))
                for ret in result:
                    for entry in entries:
                        if ret["no"] == entry["no"]:
                            break
                    else:
                        logging.debug("no break")
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


class MarkReadHandler(BaseHandler):
    '''mark a news to readed'''

    def post(self, news_no):
        self.mark_readed(int(news_no))


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
    (r"/close", CloseHandler),
    (r"/update", UpdateHandler),
    (r"/mark(\d+)", MarkReadHandler),
    (r"/getcontent/(\d+)", ContentGetHandler),
], **settings)


def main():
    import sys
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(getattr(sys, 'PORT', 8000))

    tornado.options.parse_command_line(sys.argv)
    if settings['debug']:  # if debug on, change logging level
        logging.getLogger().setLevel(logging.DEBUG)

    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
