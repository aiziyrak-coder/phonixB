"""Gunicorn — ishlab chiqarish loglari va worker soni (monitoring uchun access log stdout)."""

import multiprocessing
import os

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
_cpu = multiprocessing.cpu_count() or 2
_default_workers = max(2, min(8, _cpu * 2 + 1))
workers = int(os.environ.get('WEB_CONCURRENCY', str(_default_workers)))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')  # stdout
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
access_log_format = os.environ.get(
    'GUNICORN_ACCESS_FORMAT',
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
)
capture_output = True
