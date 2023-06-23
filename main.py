from aiohttp import web

from amuletbackend.app import create_server_app


if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    parser = ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    web.run_app(create_server_app(), host=args.host, port=args.port)
