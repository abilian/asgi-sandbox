Minij Proxy 
===========

Goal
----

Make a proxy that adds CORS headers to GET request for use by the Minij
search engine.

Current state
-------------

1) Trying to figure out the best (best efficiency / elegance compromise) approach:

- Application: WSGI (sync) vs. ASGI (async)

   - WSGI: WebOb vs. Werkzeug (-> they are mostly interchangeable for what we need).

   - ASGI: Starlette, Blacksheep, Hug (-> Starlette is probably enough)

- Client: Requests (sync) vs. httpx and aiohttp.client (async)
  
- Server: Gunicorn, Uvicorn, Gunicorn+Uvicorn, uWsgi...

2) Running benchmarks:

See: src/benchmarks.py. Some results are currently a bit surprising so this is a WIP.


TODO
----

1) Finish benchmarks and choose an approach.

2) Make a Buildout recipe for deployment on Rapid.Space.

3) Test and iterate
