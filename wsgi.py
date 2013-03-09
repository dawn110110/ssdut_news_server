import tornado.web
import tornado.wsgi
from server import url_map, settings

application = tornado.wsgi.WSGIApplication(url_map, **settings)
