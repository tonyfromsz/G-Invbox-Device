# -*- coding: utf-8 -*-
import ujson as json
import logging

logger = logging.getLogger()


class WSProxy(object):

    all_sockets = {}

    @classmethod
    def add_socket(cls, device_id, socket):
        cls.all_sockets[device_id] = socket

    @classmethod
    def send_to(cls, device_id, api_name, data):
        assert isinstance(data, dict)

        if device_id not in cls.all_sockets:
            logger.error("Connection Not Detected For Device(%s)", device_id)
            return
        socket = cls.all_sockets[device_id]

        params = {
            "header": {
                "apiName": api_name,
            },
            "body": data
        }
        text = json.dumps(params)
        logger.info("[WebSocket] %s %s %s", device_id, api_name, text)
        socket.write_message(text)
