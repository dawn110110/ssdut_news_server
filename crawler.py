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
from renren import RenRen
import heapq
SITE_URL = 'http://ssdut.dlut.edu.cn'


class SSdutSiteCrawler(object):
    def __init__(self):
        ''' use tornaod LogFormatter '''
        self._news_url_template = string.Template(
            SITE_URL+"/index.php/News/student/p/$p/")
        self._init_going = False
        self.renren = RenRen()
        self.renren.login(config.renren_email, config.renren_pw)  # login
        self.post_queue = []  # this is a heapq of new's id

    def page_url(self, p):
        url = self._news_url_template.substitute(p=p)
        logging.debug("page url = %r" % url)
        return url

    def get_page_result(self, p):
        src = urlopen(self.page_url(p)).read()
        return par.ssdut_news_list(src)

    def add_new_post_to_q(self, id):
        heapq.heappush(self.post_queue, id)
        print self.post_queue

    def do_one_post_in_q(self):
        self.renren.visit(514178406)
        try:
            id = heapq.heappop(self.post_queue)
        except IndexError:  # empty queue
            return
        # really post
        try:
            new = New.query.filter(New.id == id).one()
            db.ses.commit()
            s = ''.join([
                new.title,
                ' - ',
                new.publisher,
                ' ',
                'http://ssdut.dlut.edu.cn',
                new.link])
            if True:
                s = s + " 想吐槽? -> http://210.30.97.149:2358/tucao/comm/%d" % int(new.id)
            self.renren.postStatus(s)
            logging.info("POST ON RENREN: %s" % s)
        except Exception, e:
            self.add_new_post_to_q(id)  # maybe next time it could be posted
            db.ses.rollback()
            traceback.print_exc()

    def update_db(self, p=1):
        self.do_one_post_in_q()  # do one post

        db_max_id = db.ses.query(func.max(New.id)).one()[0]
        db_max_record = New.query.filter(New.id==db_max_id).one()

        try:
            db.ses.commit()
        except:
            db.ses.rollback()
            db_max_id = 100000
            logging.warn("get max db record faild")
            return

        site_res = self.get_page_result(1)

        logging.info("records on site = %r, max_id in db = %r, max_url_db = %r, max_url_site = %r" %
                     (site_res.total_records, db_max_id, db_max_record.link, site_res.news_list[0]['link']))
        news_id = site_res.total_records

        # id less than db , or link different
        if db_max_id < site_res.total_records or db_max_record.link != site_res.news_list[0]['link']:
            n = site_res.total_records - db_max_id
            logging.info("max_record_on_site - max_id_in_db = %r" % n)
            # updte news here
            # assume that, n<=12
            to_be_added_list = []
            for new in site_res.news_list:
                #if n <= 0:
                #    break
                n -= 1
                logging.info("n=%r, link=%r" % (n, new['link']))
                # do update
                try:
                    src = urlopen(SITE_URL + new['link']).read()
                except:
                    logging.error("urlopen() ERROR, link = %r" % new['link'])
                    news_id -= 1
                    continue
                detail = par.ssdut_news_parse(src)

                # if link encounter the same, break

                if new['link'] == db_max_record.link:
                    logging.info("encounter same url, update stop, site_url = %r, db_max_url=%r" %(new['link'], db_max_record.link))
                    break
                elif detail['title'] == db_max_record.title:
                    logging.info("encounter same title, update stop, site_url = %r, db_max_url=%r, site_title=%r, db_title=%r" %(new['link'],
                                                                                                                    db_max_record.link,
                                                                                                                    detail['title'],
                                                                                                                    db_max_record.title))
                    break
                elif detail['sha1'] == db_max_record.title:
                    logging.info("encounter same sha1, update stop, site_url = %r, db_max_url=%r, site_sha1=%r, db_sha1=%r" %(new['link'],
                                                                                                                    db_max_record.link,
                                                                                                                    detail['sha1'],
                                                                                                                    db_max_record.sha1))
                    break
                elif detail['body'] == db_max_record.body:
                    logging.info("encounter same body, update stop, site_url = %r, db_max_url=%r, site_sha1=%r, db_sha1=%r" %(new['link'],
                                                                                                                    db_max_record.link,
                                                                                                                    detail['body'],
                                                                                                                    db_max_record.body))
                    break
                else:
                    logging.info("! a new thread find, new_url = %r, db_max_url= %r" % (new['link'], db_max_record.link))
                    to_be_added_list.append(new)
            to_be_added_len = len(to_be_added_list)
            logging.info("%r  records will be added" % to_be_added_len)

            for new in to_be_added_list:

                try:
                    src = urlopen(SITE_URL + new['link']).read()
                except:
                    logging.error("urlopen() ERROR, link = %r" % new['link'])
                    news_id -= 1
                    continue
                finally:
                    to_be_added_len -= 1
                detail = par.ssdut_news_parse(src)
                r = New(
                    id=to_be_added_len + db_max_id + 1,
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
                logging.info("%r added to db, id = %r, link = %r" % (r, r.id, r.link))
                db.ses.add(r)
                try:
                    db.ses.commit()
                except:
                    db.ses.rollback()
                    logging.error("session commit error, when add %r" % r)

                #  add a post to queue
                s = self.add_new_post_to_q(r.id)
        else:
            pass
        logging.debug("update finish")

    def reset_news_db(self):
        ''' get the first 10 pages news and store them in db'''
        logging.warn("reset_news_db called, but will have no effect")
        return  # just return

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
    lg.setLevel(logging.INFO)

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
