#!/usr/bin/env python
#encoding=utf-8
from BeautifulSoup import BeautifulSoup as bsoup
from HTMLParser import HTMLParser
from utils import re_compile, Storage, timed
from hashlib import sha1
import datetime

__all__ = ['html_parser', 'ssdut_news_parse']

html_parser = HTMLParser()


def ssdut_news_parse(raw):
    ''' parse the raw page src,

    store all results in a Storage object.
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
    result.unescaped_body
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

    print 'run 10 times'
    result = testing(10)
    # run 10 times
    # testing() took 0.6200559139251709 secs to finish

    print "\n---", result.publisher
    print "\n---", result.clean_body[:20], '....'
    print "\n---", result.body[:20], '.....'
    print "\n---", result.date
    print "\n---", result.source
    print "\n---", result.title
    print "\n---", result.sha1
