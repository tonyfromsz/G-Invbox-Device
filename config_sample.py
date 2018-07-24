# encoding=utf-8

'''
配置以Docker运行时为准，开发环境自己cp config.py后修改
'''


class Config(object):

    domain = "http://invbox.yuiitec.com"

    # logging settings
    log_level = 'INFO'
    log_path = '/src/logs'

    media_path = "/src/data/media"
    amqp_uri = "pyamqp://rbt:rbt123@172.18.224.101:5673"


config = Config()
