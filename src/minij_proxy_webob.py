import fire
import paste.httpserver
import requests
import webob
from gunicorn.app.base import BaseApplication

# Extremely aggressive and hardcoded value

TIMEOUT = 10

DEFAULT_ACCESS_URL = "https://mynij.app.officejs.com"


def application(environ, start_response):
    request = webob.Request(environ)
    response = webob.Response()

    if request.method != "GET":
        response.status = 405
    else:
        fetch_content(request, response)

    return response(environ, start_response)


def fetch_content(request: webob.Request, response: webob.Response) -> None:
    url = request.GET["url"]
    proxy_query_header = make_request_headers(request.headers)

    try:
        proxy_response = requests.get(url, headers=proxy_query_header, timeout=TIMEOUT)
    except requests.exceptions.SSLError:
        # Invalid SSL Certificate
        response.status = 526
    except requests.exceptions.ConnectionError:
        response.status = 523
    except requests.exceptions.Timeout:
        response.status = 524
    except requests.exceptions.TooManyRedirects:
        response.status = 520
    else:
        response.body = proxy_response.content
        if proxy_response.status_code == 500:
            response.status = 520
        else:
            copy_proxy_headers(proxy_response, response)

    response.headers["Access-Control-Allow-Origin"] = get_access_url(request.headers)


def make_request_headers(headers: dict):
    request_headers = {}
    HEADERS = [
        "Content-Type",
        "Accept",
        "Accept-Language",
        "Range",
        "If-Modified-Since",
        "If-None-Match",
    ]
    for k in HEADERS:
        v = headers.get(k)
        if v:
            request_headers[k] = str(v)

    return request_headers


def copy_proxy_headers(proxy_response, response) -> None:
    HEADERS = [
        "Content-Disposition",
        "Content-Type",
        "Date",
        "Last-Modified",
        "Vary",
        "Cache-Control",
        "Etag",
        "Accept-Ranges",
        "Content-Range",
    ]
    for k, v in proxy_response.headers.items():
        k = k.title()
        if k in HEADERS:
            response.headers[k] = v


def get_access_url(headers: dict):
    return headers.get("Origin", DEFAULT_ACCESS_URL)


class GunicornApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main(host="localhost", port=8000, server="wsgiref", workers=10, threads=10):
    if server == "wsgiref":
        from wsgiref.simple_server import make_server

        httpd = make_server(host, port, application)
        httpd.serve_forever()

    elif server == "paste":
        paste.httpserver.serve(application, host=host, port=port)

    elif server == "gunicorn":
        options = {
            "bind": f"{host}:{port}",
            "workers": workers,
            "threads": threads,
        }
        GunicornApplication(application, options).run()


if __name__ == "__main__":
    fire.Fire(main)
