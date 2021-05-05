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
      
    - Server: Gunicorn, Uvicorn, Gunicorn+Uvicorn, uWsgi, Hypercorn...

        See: https://docs.gunicorn.org/en/latest/design.html#choosing-a-worker-type

2) Running benchmarks:

    See: src/benchmarks.py. Some results are currently a bit surprising so this is a WIP.
    
    See also: https://gist.github.com/imbolc/15cab07811c32e7d50cc12f380f7f62f for a code example.

    And: https://blog.miguelgrinberg.com/post/ignore-all-web-performance-benchmarks-including-this-one

TODO
----

1) Finish benchmarks and choose an approach.

    Actually we will probably go with:

    - Starlette
    - httpx (ou aiohttp.client)
    - Gunicorn + uvicorn (`gunicorn -k uvicorn.workers.UvicornWorker`, see: <https://www.uvicorn.org/deployment/>)
    - Do we need Nginx in front ? I don't think so but this remains an option.

    But this may change after we complete de benchmarks.

2) Make a Buildout recipe for deployment on Rapid.Space.

3) Test and iterate
