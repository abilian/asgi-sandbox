import atexit
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass

import psutil
import requests
from devtools import debug

DURATION = 30
URL = "http://localhost:{port}/?url=http://localhost:8001/"
CLIENT_CMD = 'wrk -t 10 -d {duration} "{url}"'


@dataclass
class Server:
    app: str
    port: int
    workers: int
    # cmd_tpl: str = ""

    @property
    def cmd(self):
        return self.cmd_tpl.format(app=self.app, port=self.port, workers=self.workers)

    @property
    def args(self):
        return shlex.split(self.cmd)

    @property
    def url(self):
        return URL.format(port=self.port)

    @property
    def client_cmd(self):
        return CLIENT_CMD.format(duration=DURATION, url=self.url)

    def run_bench(self) -> float:
        self.assert_stopped()

        self.start()

        time.sleep(1)
        self.assert_started()

        assert int(open("server.pid").read()) == self.process.pid

        client = self.start_benchmark()
        speed = self.get_results(client)
        time.sleep(1)

        (gone, alive) = kill_proc_tree(self.process.pid)
        # debug(gone, alive)
        assert not alive
        self.kill()
        time.sleep(1)

        print("\n")

        return speed

    def start(self) -> None:
        print(f"# Starting server: {self.cmd}")
        self.process = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=devnull)
        child_processes.append(self.process)

    def kill(self) -> None:
        print("# Shutting down server")
        self.process.kill()
        return_code = self.process.wait()
        assert return_code == self.process.returncode

    def start_benchmark(self) -> subprocess.CompletedProcess:
        print(f"# Starting benchmark")
        client_args = shlex.split(self.client_cmd)
        # debug(client_args)
        client = subprocess.run(client_args, capture_output=True)
        return client

    def get_results(self, client) -> float:
        lines = client.stdout.decode("utf-8").split("\n")
        for line in lines:
            m = re.match("Requests/sec:.*?([0-9.]+)", line)
            if m:
                speed = float(m.group(1))
                print(f"Speed: {speed} req/s")
                return speed
        return -1.0

    def assert_started(self):
        r = requests.get(self.url)
        assert r.status_code == 200

    def assert_stopped(self):
        try:
            r = requests.get(self.url)
            raise AssertionError("Server is not stopped")
        except:
            pass


class Gunicorn(Server):
    type = "wsgi"
    label = "Gunicorn"
    cmd_tpl = "gunicorn -b localhost:{port} --pid server.pid -w {workers} {app}"


class Uwsgi(Server):
    type = "wsgi"
    label = "uWsgi"
    cmd_tpl = "uwsgi --pidfile server.pid --http localhost:{port} -w {app} -L -p {workers}"


class GunicornUvicorn(Server):
    type = "asgi"
    label = "Gunicorn+Uvicorn"
    cmd_tpl = "gunicorn -b localhost:{port} --pid server.pid " \
        "-k uvicorn.workers.UvicornWorker -w {workers} {app}"


class Hypercorn(Server):
    type = "asgi"
    label = "Hypercorn"
    cmd_tpl = "hypercorn -b localhost:{port} --pid server.pid -w {workers} -k uvloop {app}"


SERVER_CLASSES = [Uwsgi, Gunicorn, GunicornUvicorn, Hypercorn]


APPLICATIONS = {
    "asgi": [
        "minij_proxy_asgi_starlette:app",
        "minij_proxy_asgi_aiohttp:application",
        "minij_proxy_asgi_httpx:application",
        "minij_proxy_falcon:app",
    ],
    "wsgi": [
        "minij_proxy_webob:application",
        "minij_proxy_werkzeug:application",
    ],
}

devnull = open("/dev/null", "wb")

results = []
child_processes = []
result_file = open("results.csv", "w")
result_file.write(f'Speed;Type;Label;App;Workers;Command"\n')
result_file.flush()

def main():
    start_caddy()

    port = 8100
    for workers in [1, 2, 4, 8, 16]:
        for server_class in SERVER_CLASSES:
            for application in APPLICATIONS[server_class.type]:
                server = server_class(application, port, workers)
                port += 1

                try:
                    speed = server.run_bench()
                    results.append((speed, server.cmd))

                    result_file.write(f'{speed};{server.type};{server.label};{server.app};{server.workers};"{server.cmd}"\n')
                    result_file.flush()
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    traceback.print_exc()
                port += 1

    report_results(results)


def start_caddy():
    print("# Starting Caddy server")
    cmd = "caddy file-server -listen localhost:8001 --root static"
    caddy = subprocess.Popen(shlex.split(cmd), stdout=devnull, stderr=devnull)
    child_processes.append(caddy)


def kill_proc_tree(
    pid, sig=signal.SIGTERM, include_parent=True, timeout=None, on_terminate=None
):
    """Kill a process tree (including grandchildren) with signal "sig" and
    return a (gone, still_alive) tuple.

    "on_terminate", if specified, is a callback function which is called
    as soon as a child terminates.
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
    gone, alive = psutil.wait_procs(children, timeout=timeout, callback=on_terminate)
    return (gone, alive)


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
