import atexit
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import traceback

import psutil
import requests
from devtools import debug

DURATION = 5
URL = "http://localhost:8000/?url=http://localhost:8001/"
CLIENT_CMD = f'wrk -t 10 -d {DURATION} "{URL}"'

COMMANDS = [
    # ASGI + Starlette + httpx
    # "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_asgi_new:app",
    "gunicorn --pid server.pid -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_asgi_new:app",
    "hypercorn --pid server.pid -w 4 -k uvloop minij_proxy_asgi_new:app",
    # ASGI + Starlette + httpx (slow)
    # "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_asgi_slow:app",
    "gunicorn --pid server.pid -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_asgi_slow:app",
    "hypercorn --pid server.pid -w 4 -k uvloop minij_proxy_asgi_slow:app",
    # # ASGI + Starlette + aiohttp.client
    # "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_asgi_aiohttp:application",
    "gunicorn --pid server.pid -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_asgi_aiohttp:application",
    "hypercorn --pid server.pid -w 4 -k uvloop minij_proxy_asgi_aiohttp:application",
    # # ASGI + Starlette + httpx
    # "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_asgi_httpx:application",
    "gunicorn --pid server.pid -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_asgi_httpx:application",
    "hypercorn --pid server.pid -w 4 -k uvloop minij_proxy_asgi_httpx:application",
    # # ASGI + Falcon
    # "uvicorn --no-access-log --workers 4 --loop uvloop minij_proxy_falcon:application",
    "gunicorn --pid server.pid -k uvicorn.workers.UvicornWorker -w 4 minij_proxy_falcon:application",
    "hypercorn --pid server.pid -w 4 -k uvloop minij_proxy_falcon:application",
    # WSGI
    "gunicorn --pid server.pid -w 4 minij_proxy_webob:application",
    "gunicorn --pid server.pid -w 4 minij_proxy_werkzeug:application",
    "uwsgi --pidfile server.pid --http localhost:8000 -w minij_proxy_webob:application -L -p 4",
    "uwsgi --pidfile server.pid --http localhost:8000 -w minij_proxy_werkzeug:application -L -p 4",
    # "waitress-serve --listen localhost:8000 minij_proxy_webob:application",
    # "waitress-serve --listen localhost:8000 minij_proxy_werkzeug:application",
]

devnull = open("/dev/null", "wb")

results = []
child_processes = []


def main():
    start_caddy()

    for command in COMMANDS:
        try:
            run_bench(command)
        except KeyboardInterrupt:
            sys.exit()
        except:
            traceback.print_exc()

    report_results(results)


def run_bench(command):
    assert_server_stopped(URL)

    server = start_server(command)
    time.sleep(1)
    assert_server_started(URL)
    assert int(open("server.pid").read()) == server.pid

    client = start_benchmark()
    update_results(results, command, client)
    time.sleep(1)

    (gone, alive) = kill_proc_tree(server.pid)
    # debug(gone, alive)
    assert not alive
    kill_server(server)
    time.sleep(1)

    print("\n")


def start_caddy():
    print("# Starting Caddy server")
    cmd = "caddy file-server -listen localhost:8001 --root static"
    caddy = subprocess.Popen(shlex.split(cmd), stdout=devnull, stderr=devnull)
    child_processes.append(caddy)


def start_server(command) -> subprocess.Popen:
    server_args = shlex.split(command)
    print(f"# Starting server: {command}")
    # debug(server_args)
    # server = subprocess.Popen(server_args)
    server = subprocess.Popen(server_args, stdout=devnull, stderr=devnull)
    child_processes.append(server)
    return server


def kill_server(server) -> None:
    print("# Shutting down server")
    server.kill()
    return_code = server.wait()
    # debug(return_code)
    # debug(server.returncode)
    assert return_code == server.returncode


def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callback function which is
    called as soon as a child terminates.
    """
    assert pid != os.getpid(), "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        try:
            p.send_signal(sig)
        except psutil.NoSuchProcess:
            pass
    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return (gone, alive)


def start_benchmark() -> subprocess.CompletedProcess:
    print(f"# Starting benchmark")
    client_args = shlex.split(CLIENT_CMD)
    # debug(client_args)
    client = subprocess.run(client_args, capture_output=True)
    return client


def update_results(results, command, client):
    lines = client.stdout.decode("utf-8").split("\n")
    for line in lines:
        m = re.match("Requests/sec:.*?([0-9.]+)", line)
        if m:
            speed = float(m.group(1))
            print(f"Speed: {speed} req/s")
            results.append((speed, command))


def assert_server_started(url):
    r = requests.get(url)
    assert r.status_code == 200


def assert_server_stopped(url):
    try:
        r = requests.get(url)
        raise AssertionError("Server is not stopped")
    except:
        pass


def report_results(results):
    results.sort(reverse=True)
    for speed, cmd in results:
        print(f"{speed:>10} | {cmd}")


def reap_child_processes():
    for p in child_processes:
        print(f"Reaping child process: {p}")
        p.kill()
        p.wait()


atexit.register(reap_child_processes)

main()
