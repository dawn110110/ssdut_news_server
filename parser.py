#!/usr/bin/env python
#encoding=utf-8
from BeautifulSoup import BeautifulSoup as bsoup
from HTMLParser import HTMLParser
from utils import re_compile, Storage, timed
from hashlib import sha1
import datetime
import logging

__all__ = ['html_parser', 'ssdut_news_parse']

SSDUT_SITE = "http://ssdut.dlut.edu.cn"

html_parser = HTMLParser()


def ssdut_news_list(page_raw):
    ''' parse the news_list page,
    get a list of news, the same squence as the page,

    result.soup
          .page_no
          .news_list
          .total_records
    '''
    result = Storage()
    soup = bsoup(page_raw)
    result.soup = soup

    # get current page number
    r = soup.find(text=ur"\u4e0b\u4e00\u9875")  # text=u"下一页"
    if r:
        '''not the last page'''
        next_page_link = r.parent.attrs[0][1]
        #logging.debug("r.parent.attrs = %r" % r.parent.attrs)
        r = re_compile(r'/p/(\d+)')
        page_no = r.search(next_page_link).group(1)
        page_no = int(page_no)  # - 1
    else:
        ''' the last page'''
        r = soup.find(text=ur'\u4e0a\u4e00\u9875')
        prev_page_link = r.parent.attrs[0][1]
        logging.debug("r.parent.attrs = %r" % r.parent.attrs)
        r = re_compile(r'/p/(\d+)')
        page_no = r.search(prev_page_link).group(1)
        page_no = int(page_no)  # + 1
    result.page_no = page_no

    # get the news list
    res = soup.findAll(attrs={"bgcolor": "#EEEEEE"})
    news_list = []
    counter = 1
    for r in res:
        a = r.findChildren("a")
        date_str = r.find(text=re_compile("\d{4}-\d{2}-\d{2}")).encode("utf-8")
        news_list.append(
            {
                "link": a[0].get("href").encode("utf-8"),
                "title": a[0].text.encode("utf-8"),
                "source": a[1].text.encode("utf-8"),
                "source_link": a[1].get("href").encode("utf-8"),
                "date_str": date_str,
                "date": datetime.date(
                    *[int(n) for n in date_str.split("-")]),
                "no": counter,
            })
        counter += 1
        #logging.debug("source = %s, source_link = %s" %
        #              (news_list[-1]['source'], news_list[-1]['source_link']))
    result.news_list = news_list

    # tital news num
    # 共\d+ t条记录
    s = soup.find(text=re_compile(ur"\u5171\d+ \u6761\u8bb0\u5f55"))
    r = re_compile(ur"\u5171(\d+)")
    result.total_records = int(r.search(s).group(1))

    return result


def ssdut_news_parse(raw):
    ''' parse the raw page src,

    store all result in a Storage object.
    all strings are unicode

    result.soup
        BeautifulSoup object
    result.raw
        raw page src
    result.hash
        sha1 hash of the page
    result.title
        title
    result.source
        来源
    result.date_str - date in string
    result.date - date object
    result.body
        html src of the news body
    result.clean_body
        unescaped src of the news body,
    result.publisher
        发表人
    '''
    soup = bsoup(raw)
    result = Storage()

    # raw page / hash
    result.raw = raw
    result.sha1 = sha1(soup.text.encode("utf-8")).hexdigest()
    result.soup = soup

    # title
    s = soup.find(attrs={'class': re_compile('title')})
    result.title = s.text

    # source
    text = soup.find(text=re_compile(r"^http://ssdut.dlut.edu.cn"))
    r = re_compile(
        ur"(\d+-\d+-\d+)\u3000\u3000\u6765\u6e90:(.+)\u5173\u6ce8:")
    res = r.findall(text)[0]
    result.source = res[1].rstrip()

    # date
    result.date_str = res[0]
    result.date = datetime.date(*[int(n) for n in result.date_str.split('-')])

    # content (body)
    c = soup.find(attrs={'class': re_compile('content')})
    result.body = unicode(c)

    # content (body)  unescaped
    texts = c.findAll(text=True)
    all_texts = '\n'.join(texts)
    result.clean_body = html_parser.unescape(all_texts)

    # publisher (could be find at the bottom of page)
    s = soup.find(
        attrs={
            "style": "font-size:14px;float:left;text-align:right;width:80%"
        })
    r = re_compile(ur"\u53d1\u8868\u4eba\uff1a(.+)")
    name = r.findall(s.text)[0]
    result.publisher = name.rstrip().lstrip()

    # use utf-8 encoding
    for k in ['title', 'source', 'body', 'clean_body', 'publisher']:
        result[k] = result[k].encode('utf-8')
    result.search_text = ''.join([result.title, result.source,
                                  result.clean_body, result.publisher,
                                  result.sha1])

    return result


def parse_on_url(url):
    # get page
    # parse
    pass


def parse_on_id(url):
    # get link
    # parse
    pass

if __name__ == "__main__":
    from urllib2 import urlopen

    src = urlopen("http://ssdut.dlut.edu.cn/index.php/News/10060.html").read()

    @timed
    def testing(t):
        for i in xrange(t):
            result = ssdut_news_parse(src)
        return result

    #print 'run 10 times'
    result = testing(1)
    # run 10 times
    # testing() took 0.6200559139251709 secs to finish

    print "\n---", result.publisher
    print "\n---", result.clean_body[:20], '....'
    print "\n---", result.body[:20], '.....'
    print "\n---", result.date
    print "\n---", result.source
    print "\n---", result.title
    print "\n---", result.sha1

    #ssdut_news_list
    print "*"*20
    site = urlopen("http://ssdut.dlut.edu.cn/index.php/News/student.html")
    src = site.read()
    site.close()

    result = ssdut_news_list(src)
    print result.page_no
    print result.total_records
    print len(result.news_list)
    print result.news_list[0]

