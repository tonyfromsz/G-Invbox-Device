# -*- coding: utf-8 -*-

from nameko.standalone.rpc import ClusterRpcProxy
from config import config


def RPCClient():
    return ClusterRpcProxy({"AMQP_URI": config.amqp_uri})
