# coding=utf-8
import sys
import tornado.httpserver
from tornado.options import define, parse_command_line, options

from log import init_logger
from config import config
from controller import init_controllers
from controller.route import Route

reload(sys)
sys.setdefaultencoding("utf-8")


define("port", type=int, default=8000,
       help="the server port")
define("address", type=str, default='0.0.0.0',
       help="the server address")
define("debug", type=bool, default=False,
       help="switch debug mode")
parse_command_line()

init_controllers()
urls = Route.routes()

init_logger(path=config.log_path, level=config.log_level)

application = tornado.web.Application(urls,
                                      cookie_secret="fa5012f23340edae6db5df925b345912",
                                      autoreload=options.debug)
app_server = tornado.httpserver.HTTPServer(application, xheaders=True)
app_server.listen(options.port, options.address)
print "server running..."
tornado.ioloop.IOLoop.instance().start()
