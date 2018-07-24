# -*- coding: utf-8 -*-
import ujson as json
import logging

from tornado.websocket import WebSocketHandler
from controller.route import Route, WSApi
from ws_util import WSProxy

logger = logging.getLogger(__name__)


@Route("/ws")
class MainWebSocket(WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        origin = self.request.headers.get("Origin", "")
        device_id = self.request.headers.get("deviceId")
        logger.info("Connection Established: %s, %s", origin, device_id)
        WSProxy.add_socket(device_id, self)

    def on_message(self, message):
        logger.info("Message Recevied: %s" % message)

        try:
            data = json.loads(message)
        except:
            logger.error("Invalid Json")
            return

        if "header" not in data or "body" not in data:
            logger.error("Lack header or body")
            return
        header, body = data["header"], data["body"]

        if "apiName" not in header and "deviceId" not in header or "clientIp" not in header:
            logger.error("Lack apiName or deviceId or clientIp")
            return

        api_name = header["apiName"]
        routers = WSApi.routes()
        if api_name not in routers:
            logger.error("Not Found WSApi: %s", api_name)
            return

        self.device_id = header["deviceId"]
        self.client_ip = header["clientIp"]
        apifunc = routers[api_name]
        apifunc(self, body, header=header)

    def on_close(self):
        origin = self.request.headers.get("Origin", "")
        logger.info("Connection Closed: %s", origin)

    def on_ping(self):
        origin = self.request.headers.get("Origin", "")
        logger.info("on ping: %s", origin)

    def on_pong(self):
        origin = self.request.headers.get("Origin", "")
        logger.info("on pong: %s", origin)
