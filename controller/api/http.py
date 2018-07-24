# -*- coding: utf-8 -*-
import ujson as json
import qrcode
import os
import logging

from nameko_util import RPCClient
from tornado.web import StaticFileHandler
from controller.route import Route, HttpApi
from controller.handler import VersionedHandler, HttpError
from config import config
from util import dict_to_xml
from io import BytesIO

logger = logging.getLogger(__name__)


@Route("/http")
class MainHttpHandler(VersionedHandler):

    def get_version(self):
        return "1.0"

    def prepare(self):
        try:
            data = json.loads(self.request.body)
        except:
            raise HttpError(400, "INVALID_JSON", "json格式错误")

        if "header" not in data or "body" not in data:
            raise HttpError(400, "INVALID_PARAMS", "缺少header或body字段")

        self.header = data["header"]
        self.body = data["body"]
        if "apiName" not in self.header or "deviceId" not in self.header:
            raise HttpError(400, "INVALID_PARAMS", "缺少apiName或devcieId字段")

        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip

        self.api_name = self.header["apiName"]
        self.device_id = self.header["deviceId"]
        self.client_ip = remote_ip

    def post(self):
        apis = HttpApi.apis()
        if self.api_name not in apis:
            raise HttpError(400, "INVALID_APINAME", "%s Not Found" % self.api_name)
        api_func = apis[self.api_name]
        logger.info("[request] api_name: %s, device_id: %s, client_ip: %s, called_func: %s",
                    self.api_name, self.device_id, self.client_ip, api_func.__name__)
        return api_func(self)


@Route("/orders/(?P<order_no>\w+)/qrcode")
class PayQRCodeHandler(VersionedHandler):
    """
    测试用；设备并不使用这个接口。
    """

    def get(self, order_no):
        with RPCClient() as rpc:
            info = rpc.invbox.get_qrcode_url(order_no)

        code_url = info.get("qrcodeUrl", "")
        if code_url:
            res_info = code_url
        else:
            res_info = u"二维码失效"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=1
        )

        qr.add_data(res_info)
        img = qr.make_image()
        byte_io = BytesIO()
        img.save(byte_io, 'PNG')
        byte_io.seek(0)

        self.set_header('Content-Type', 'image/png')
        return self.write(byte_io.getvalue())


@Route("/wxnotify")
class WXNotifyHandler(VersionedHandler):

    def post(self):
        logger.info("Received WXPay Result: %s", self.request.body)

        with RPCClient() as rpc:
            rpc.invbox.wxpay_notify(self.request.body)

        response = {
            "return_code": "SUCCESS",
            "return_msg": "OK",
        }
        return self.write(dict_to_xml(response))


@Route("/alinotify")
class AliNotifyHandler(VersionedHandler):

    def post(self):
        logger.info("Received AliPay Result: %s", self.request.body.decode("gbk"))
        with RPCClient() as rpc:
            rpc.invbox.alipay_notify(self.request.body)
        return self.write("success")


@Route('/media/(.*)', {"path": config.media_path})
class MediaHandler(StaticFileHandler):
    pass


@HttpApi("getItemList")
def get_items(handler):
    with RPCClient() as rpc:
        data = rpc.invbox.get_items_for_device(handler.device_id, config.domain)

    result = []
    for item_info in data:
        result.append({
            "itemId": item_info["id"],
            "itemType": item_info["category"],
            "price": float(item_info["price"]) / 100,
            "name": item_info["name"],
            "thumbnail": item_info["thumbnail"],
            "description": item_info["description"],
            "stock": item_info["stock"],
            "road": item_info["road"]
        })

    return handler.write_json(result)


@HttpApi("getCtgrOfPrdt")
def get_category(handler):
    with RPCClient() as rpc:
        lst = rpc.invbox.get_categories_for_device(handler.device_id, config.domain)

    categories = []
    for d in lst:
        categories.append({
            "categoryId": d["id"],
            "name": d["name"],
            "imageUrl": d["thumbnail"],
            "description": d["description"],
        })

    return handler.write_json({"category": categories})


@HttpApi("getCtgrDtls")
def get_category_detail(handler):
    body = handler.body
    category_id = int(body["categoryId"])

    with RPCClient() as rpc:
        lst = rpc.invbox.get_categories_for_device(handler.device_id, config.domain)

    choose = {}
    for d in lst:
        if d["id"] == category_id:
            choose = d
            break
    if not choose:
        return handler.write_json({})

    items = []
    for item_info in choose["items"]:
        items.append({
            "itemId": item_info["id"],
            "itemType": choose["name"],
            "price": item_info["price"],
            "name": item_info["name"],
            "thumbnail": item_info["thumbnail"],
            "description": item_info["description"],
        })

    result = {
        "imageUrl": d["imageUrl"],
        "productList": items,
    }
    return handler.write_json(result)


@HttpApi("exchangeItem")
def exchange_item(handler):
    "兑换商品"
    body = handler.body
    stype = body.get("type", "")

    if stype not in ["redeem", "voiceCode"]:
        raise HttpError(400, "PARAM_ERROR", "type字段取值错误")

    if stype == "voiceCode" and "user_id" not in body:
        raise HttpError(400, "PARAM_ERROR", "缺少user_id字段")

    with RPCClient() as rpc:
        if stype == "redeem":
            res = rpc.invbox.exchange_item_by_redeem(handler.device_id,
                                                     body["code"])
        else:
            user_id = body["user_id"]
            res = rpc.invbox.exchange_item_by_voice(handler.device_id,
                                                    body["code"],
                                                    user_id)
    if res["resultCode"]:
        raise HttpError(400, "FAIL", res["resultMsg"])
    return handler.write_json(res)


@HttpApi("submitOrder")
def create_order(handler):
    body = handler.body
    if "payType" not in body:
        body["payType"] = 1

    pay_type = body["payType"]
    if pay_type == 1:
        notify_url = config.domain + "/wxnotify"
    elif pay_type == 2:
        notify_url = config.domain + "/alinotify"

    with RPCClient() as rpc:
        order_info = rpc.invbox.create_order(handler.device_id,
                                             body["itemId"],
                                             body["amount"],
                                             pay_type,
                                             notify_url)
        if order_info["resultCode"]:
            return handler.write_json({
                "resultCode": 1,
                "resultMsg": order_info["resultMsg"],
            })
    return handler.write_json(order_info)


@HttpApi("getOrder")
def get_order(handler):
    body = handler.body

    with RPCClient() as rpc:
        order_info = rpc.invbox.get_order_detail(body["orderNo"])
        if not order_info:
            raise HttpError(400, "NOT_FUNCD_ORDER", "未找到订单信息")

    data = {
        "orderNo": order_info["orderNo"],
        "deviceBoxNo": order_info["roadNo"],
        "itemAmount": order_info["itemAmount"],
        "item": order_info["item"],
        "payMoney": order_info["payMoney"],
        "orderStatus": order_info["status"],
        "payAt": order_info["payAt"],
        "payType": order_info["payType"] or 0,
    }

    return handler.write_json(data)


@HttpApi("deliverResult")
def client_deliver_result(handler):
    body = handler.body
    with RPCClient() as rpc:
        if body["resultCode"] == "SUCCESS":
            rpc.invbox.deliver_result(body["orderNo"], True)
        else:
            rpc.invbox.deliver_result(body["orderNo"], False)
    return handler.write_json({"status": "SUCCESS"})


@HttpApi("getNewestAPK")
def get_latest_apk(handler):
    with RPCClient() as rpc:
        data = rpc.invbox.get_newest_apk()
    if not data:
        return handler.write_json(data)
    data = {
        "version": data["version"],
        "downloadUrl": config.domain + data["downloadUrl"]
    }
    return handler.write_json(data)


@HttpApi("getAdsOfA")
def get_ads_of_a(handler):
    with RPCClient() as rpc:
        data = rpc.invbox.get_device_ads(handler.device_id)

    if not data:
        return handler.write_json({})

    res = {
        "text": data["aText"].split("\n"),
        "videos": data["aVideos"]
    }
    for d in res.get("videos"):
        if not d["videoUrl"].startswith("http"):
            d["videoUrl"] = config.domain + d["videoUrl"]
        d["videoName"] = os.path.split(d["videoUrl"])[1]
    return handler.write_json(res)


@HttpApi("getAdsOfB")
def get_ads_of_b(handler):
    with RPCClient() as rpc:
        data = rpc.invbox.get_device_ads(handler.device_id)

    if not data:
        return handler.write_json({})

    res = {
        "images": data["bImages"]
    }
    for d in res.get("images"):
        d["imageUrl"] = config.domain + d["imageUrl"]
    return handler.write_json(res)


@HttpApi("getAdsOfC")
def get_ads_of_c(handler):
    with RPCClient() as rpc:
        data = rpc.invbox.get_device_ads(handler.device_id)

    if not data:
        return handler.write_json({})

    res = {
        "images": data["cImages"]
    }
    for d in res.get("images"):
        d["imageUrl"] = config.domain + d["imageUrl"]
    return handler.write_json(res)


@HttpApi("getPermission")
def get_permission(handler):
    body = handler.body
    token = body.get("token", "")

    mappings = {
        "buhuo2018": "suppler",
        "yhfxfh2018": "admin"
    }

    if token not in mappings:
        raise HttpError(400, "INVALID_TOKEN", "无效token")

    return handler.write_json({"role": mappings[token]})


@HttpApi("finishSupply")
def finishSupply(handler):
    body = handler.body
    device_id = handler.device_id

    with RPCClient() as rpc:
        data = rpc.invbox.finish_supply(device_id, body["no"])

    if data["resultCode"]:
        raise HttpError(400, "SUPPLY_FAIL", data["resultMsg"])
    return handler.write_json({})


@HttpApi("heartbeat")
def heartbeat(handler):
    device_id = handler.device_id
    client_ip = handler.client_ip
    with RPCClient() as rpc:
        rpc.invbox.online_heartbeat(device_id, client_ip)
    return handler.write_json({"status": "SUCCESS"})


@HttpApi("writeLog")
def write_client_log(handler):
    device_id = handler.device_id
    body = handler.body

    if "type" not in body or "data" not in body:
        raise HttpError(400, "LACK_PARAM", "缺少参数")
    stype = body["type"]
    data = body["data"]

    logger.info('[client] "%s" "%s" "%s"' % (device_id, stype, data))
    return handler.write_json({})
