#!/usr/bin/env python
#encoding=utf-8

from models import *
import db
import parser as par
from config import update_interval
from utils import TornadoFormatter
import time
import logging
import urllib2
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
        logging.info("page url = %r" % url)
        return url

    def get_page_result(self, p):
        src = urlopen(self.page_url(p)).read()
        return par.ssdut_news_list(src)

    def update_db(self, p=1):
        # TODO  fix hole , update
        logging.debug("Update begin")

        res = self.get_page_result(1)

        logging.info("total records on site = %r" % res.total_records)
        logging.debug("kv.total_records = %r" % kv.total_records)

        if kv.total_records < res.total_records:
            logging.info("will update %r news" %
                         (res.total_records-kv.total_records))
            # updte news here
            kv.total_records = res.total_records
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
        for p in xrange(1, 11):
            res_list.append(self.get_page_result(p))

        # get news detail and store in db
        news_id = res_list[0].total_records
        for page in res_list:
            for new in page.news_list:
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
                    sha1=detail.sha1)
                db.ses.add(r)
                db.ses.commit()

                news_id -= 1


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

    updater.reset_news_db()
    #while True:
    #    updater.update_db()
    #    time.sleep(5)
