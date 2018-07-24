# -*- coding: utf-8 -*-
from lxml import etree


def xml_to_dict(content):
    raw = {}
    root = etree.fromstring(content)
    for child in root:
        raw[child.tag] = child.text
    return raw


def dict_to_xml(data):
    s = ""
    for k, v in data.items():
        s += "<{0}>{1}</{0}>".format(k, v)
    s = "<xml>{0}</xml>".format(s)
    return s.encode("utf-8")
