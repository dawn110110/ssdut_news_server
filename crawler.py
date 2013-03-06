#!/usr/bin/env python
#encoding=utf-8

from models import *
import traceback
from sqlalchemy import func
import db
import parser as par
import config
from utils import TornadoFormatter
import time
import logging
from urllib2 import urlopen
import string

SITE_URL = 'http://ssdut.dlut.edu.cn'


class SSdutSiteCrawler(object):
    def __init__(self):
        ''' use tornaod LogFormatter '''
        self._news_url_template = string.Template(
            SITE_URL+"/index.php/News/student/p/$p/")
        self._init_going = False

    def page_url(self, p):
        url = self._news_url_template.substitute(p=p)
        logging.debug("page url = %r" % url)
        return url

    def get_page_result(self, p):
        src = urlopen(self.page_url(p)).read()
        return par.ssdut_news_list(src)

    def update_db(self, p=1):
        # TODO  fix hole , update
        db_max_id = db.ses.query(func.max(New.id)).one()[0]

        site_res = self.get_page_result(1)

        logging.info("records on site = %r, max_id in db = %r" %
                     (site_res.total_records, db_max_id))
        news_id = site_res.total_records

        if db_max_id < site_res.total_records:
            n = site_res.total_records - db_max_id
            logging.info("will update %r news" % n)
            # updte news here
            # assume that, n<=12
            for new in site_res.news_list:
                if n <= 0:
                    break
                n -= 1
                print n
                # do update
                src = urlopen(SITE_URL + new['link']).read()
                detail = par.ssdut_news_parse(src)
                r = New(
                    id=news_id,
                    raw=detail.raw,
                    title=detail.title,
                    link=new['link'],
                    body=detail.body,
                    clean_body=detail.clean_body,
                    date=detail.date,
                    publisher=detail.publisher,
                    source=detail.source,
                    source_link=new['source_link'],
                    sha1=detail.sha1,
                    search_text=detail.search_text)
                logging.info("%r added to db, id = %r" % (r, r.id))
                db.ses.add(r)
                db.ses.commit()
                news_id -= 1
        else:
            logging.info("no news to be update")
        logging.debug("update finish")

    def reset_news_db(self):
        ''' get the first 10 pages news and store them in db'''
        # delete all records in db
        for r in New.query.all():
            db.ses.delete(r)
        db.ses.commit()
        logging.debug("delete all news records in db")

        # get all the news links
        res_list = []
        for p in xrange(1, 220):
            res_list.append(self.get_page_result(p))

        # get news detail and store in db
        news_id = res_list[0].total_records
        for page in res_list:
            for new in page.news_list:
                #try:
                src = urlopen(SITE_URL + new['link']).read()
                detail = par.ssdut_news_parse(src)
                r = New(
                        id=news_id,
                        raw=detail.raw,
                        title=detail.title,
                        link=new['link'],
                        body=detail.body,
                        clean_body=detail.clean_body,
                        date=detail.date,
                        publisher=detail.publisher,
                        source=detail.source,
                        source_link=new['source_link'],
                        sha1=detail.sha1,
                        search_text=detail.search_text)
                db.ses.add(r)
                db.ses.commit()
                logging.info("%r, added, link=%r, page_no = %r" %
                                 (r, r.link, page.page_no))
                news_id -= 1
                    #except:
                    #    traceback.print_exc()
                    #    logging.error("error, r=  %r" % r )
                    #    logging.error("page no = %r" % page.page_no)
                    #finally:
                    #    news_id -= 1


if __name__ == "__main__":
    updater = SSdutSiteCrawler()

    # set up the log format
    lg = logging.getLogger()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(TornadoFormatter(color=True))

    file_handler = logging.FileHandler('crawler.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(TornadoFormatter(color=False))

    lg.addHandler(console_handler)
    lg.addHandler(file_handler)
    lg.setLevel(logging.DEBUG)

    if kv.db_inited:
        logging.info("Initial data already loaded, begin updating")
    else:

        logging.info("begin crawling initial data...")
        updater.reset_news_db()
        kv.db_inited = 'true'
        logging.info("db init finished")

    while True:
        updater.update_db()
        time.sleep(config.update_interval)
