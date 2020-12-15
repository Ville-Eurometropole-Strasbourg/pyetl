# -*- coding: utf-8 -*-
"""
@author: claude
"""
import os


class Config(object):
    SECRET_KEY = (
        os.environ.get("SECRET_KEY")
        or "quand il n'y a pas de solution il n'y a pas de problème"
    )
    FLASKFILEMANAGER_FILE_PATH = "C:/dev/test_mapper"


appconfig = Config()
