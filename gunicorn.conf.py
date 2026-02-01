"""Gunicorn configuration for MGG_SYS production deployment"""
import os
import multiprocessing
from app.config.network_config import GUNICORN_CONFIG

# Server socket
bind = GUNICORN_CONFIG['bind']
backlog = 2048

# Worker processes
workers = GUNICORN_CONFIG['workers']
worker_class = GUNICORN_CONFIG['worker_class']
worker_connections = 1000
threads = GUNICORN_CONFIG['threads']
max_requests = GUNICORN_CONFIG['max_requests']
max_requests_jitter = GUNICORN_CONFIG['max_requests_jitter']
timeout = GUNICORN_CONFIG['timeout']
graceful_timeout = GUNICORN_CONFIG['graceful_timeout']
keepalive = GUNICORN_CONFIG['keepalive']

# Logging
accesslog = GUNICORN_CONFIG['accesslog']
errorlog = GUNICORN_CONFIG['errorlog']
loglevel = GUNICORN_CONFIG['loglevel']
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'mgg_simulation_system'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Application preloading
preload_app = GUNICORN_CONFIG['preload_app']

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info('Starting MGG Simulation System')

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info('Reloading MGG Simulation System')

def when_ready(server):
    """Called just after the server is started."""
    server.log.info('Server is ready. Spawning workers')

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f'Worker spawned (pid: {worker.pid})')

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info(f'Worker initialized (pid: {worker.pid})')

def worker_int(worker):
    """Called just after a worker received the SIGINT or SIGQUIT signal."""
    worker.log.info(f'Worker received INT or QUIT signal (pid: {worker.pid})')

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f'Worker received SIGABRT signal (pid: {worker.pid})')

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info('Forked child, re-executing.')

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f'{req.method} {req.path}')

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    pass

def child_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    server.log.info(f'Worker exited (pid: {worker.pid})')

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the worker process."""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info(f'Number of workers changed from {old_value} to {new_value}')

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info('Shutting down MGG Simulation System')
