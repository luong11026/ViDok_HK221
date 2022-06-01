# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import os

bind = '0.0.0.0:10007'
workers = os.cpu_count()
accesslog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True
secure_scheme_headers = {'X-FORWARDED-PROTOCOL': 'ssl', 'X-FORWARDED-PROTO': 'https', 'X-FORWARDED-SSL': 'on'}
timeout = 300