# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import os

bind = '0.0.0.0:5005'
workers = os.cpu_count()
accesslog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True
timeout = 300