#!/bin/bash
export SCRIPT_NAME=/vidok
gunicorn --config gunicorn-cfg.py run:app