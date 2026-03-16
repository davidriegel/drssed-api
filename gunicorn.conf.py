import multiprocessing

preload_app = False
bind = "0.0.0.0:8000"

workers = 2 # multiprocessing.cpu_count() * 2 + 1

accesslog = "-"
errorlog = "-"

loglevel = "debug"