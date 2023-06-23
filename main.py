import logging

from aiohttp import web

from amuletbackend.app import create_server_app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    web.run_app(create_server_app())
