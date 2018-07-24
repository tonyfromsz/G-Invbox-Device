# -*- coding: utf-8 -*-

import sys
import tornado.httpserver
import tornado.wsgi

from log import init_logger
from config import config
from controller import init_controllers
from controller.route import Route

reload(sys)
sys.setdefaultencoding("utf-8")


init_controllers()
urls = Route.routes()

init_logger(path=config.log_path, level=config.log_level)

app = tornado.wsgi.WSGIApplication(urls,
                              cookie_secret="fa5012f23340edae6db5df925b345912")

application = tornado.wsgi.WSGIAdapter(app)
