import atexit
import re
import shlex
import subprocess
import sys
import time

import requests
from devtools import debug

DURATION = 300
URL = "http://localhost:8000/?url=http://localhost:8001/"
CLIENT_CMD = f'wrk -t 10 -d {DURATION} "{URL}"'

COMMANDS = [
    # ASGI + Starlette + aiohttp.client
    "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_asgi_aiohttp:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_asgi_aiohttp:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -t 4 minij_proxy_asgi_aiohttp:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -w 4 -t 4 minij_proxy_asgi_aiohttp:application",
    "hypercorn -w 4 -k uvloop minij_proxy_asgi_aiohttp:application",
    # ASGI + Starlette + httpx
    "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_asgi_httpx:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_asgi_httpx:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -t 4 minij_proxy_asgi_httpx:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -w 4 -t 4 minij_proxy_asgi_httpx:application",
    "hypercorn -w 4 -k uvloop minij_proxy_asgi_httpx:application",
    # ASGI + Falcon
    "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_falcon:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_falcon:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -t 4 minij_proxy_falcon:application",
    "gunicorn -k uvicorn.workers.UvicornWorker -w 4 -t 4 minij_proxy_falcon:application",
    "hypercorn -w 4 -k uvloop minij_proxy_falcon:application",
    # WSGI
    "gunicorn -w 4 minij_proxy_webob:application",
    "gunicorn -w 4 minij_proxy_werkzeug:application",
    "gunicorn -w 4 -t 4 minij_proxy_webob:application",
    "gunicorn -w 4 -t 4  minij_proxy_werkzeug:application",
    "gunicorn -t 4 minij_proxy_webob:application",
    "gunicorn -t 4 minij_proxy_werkzeug:application",
    "uwsgi --http localhost:8000 -w minij_proxy_webob:application -L -p 4",
    "uwsgi --http localhost:8000 -w minij_proxy_werkzeug:application -L -p 4",
]

devnull = open("/dev/null", "wb")

results = []
child_processes = []


def main():
    for command in COMMANDS:
        try:
            r = requests.get(URL)
            sys.exit()
        except:
            pass

        server_args = shlex.split(command)
        print(f"# Starting server: {command}")
        server = subprocess.Popen(server_args, stdout=devnull, stderr=devnull)
        child_processes.append(server)

        time.sleep(1)

        r = requests.get(URL)
        assert r.status_code == 200

        print(f"# Starting benchmark")
        client_args = shlex.split(CLIENT_CMD)
        client = subprocess.run(client_args, capture_output=True)
        lines = client.stdout.decode("utf-8").split("\n")
        for line in lines:
            m = re.match("Requests/sec:.*?([0-9.]+)", line)
            if m:
                speed = float(m.group(1))
                print(f"Speed: {speed} req/s")
                results.append((speed, command))

        # print(client.stdout.decode("utf8"))

        time.sleep(1)

        print("# Shutting down server")
        server.kill()
        return_code = server.wait()
        time.sleep(1)

        print("\n")

    results.sort()
    for speed, cmd in results:
        print(speed, cmd)


def reap_child_processes():
    for p in child_processes:
        print(f"Reaping child process: {p}")
        p.wait()


atexit.register(reap_child_processes)

main()
