import json
import os
from logging import getLogger
from pathlib import Path

import amulet
from aiohttp import web
from amulet.api.errors import LoaderNoneMatched

from amuletbackend.server import AmuletServer

log = getLogger(__name__)


def create_server_app(app: web.Application = None):
    if app is None:
        app = web.Application()

    amul = AmuletServer()
    routers = web.RouteTableDef()

    @routers.get("/")
    async def handle_(_: web.Request):
        return web.HTTPFound("/info")

    @routers.get("/info")
    async def handle_info(_: web.Request):
        return web.HTTPOk(text=json.dumps(dict(
            app_version=amul.version,
            amulet_version=amulet.__version__,
            runningProcessCount=len(amul.running_processes),
            runningProcesses=[dict(
                processor=type(proc).__name__,
                info=proc.info(),
            ) for proc in amul.running_processes],
            openFileCount=len(amul.open_files),
        ), ensure_ascii=False))

    @routers.post("/convert")
    async def handle_convert(req: web.Request):
        try:
            source_file = Path(req.query["source"]).absolute()
            # source_format = req.query["source_format"]
            target_file = Path(req.query["target"]).absolute()
            target_format = req.query["targetFormat"]
            target_platform = req.query["targetPlatform"]
            target_version = req.query["targetVersion"]
            target_version = tuple(map(int, target_version.split(".")))

        except (KeyError, ValueError) as e:
            return web.HTTPBadRequest(
                text=json.dumps(dict(result=False, type="invalid request", message=f"no specified {e} parameter"),
                                ensure_ascii=False)
            )

        try:
            if not source_file.exists():
                raise ValueError(f"Not exists path: {source_file}")
            source = await amul.load_file(source_file)
        except (LoaderNoneMatched, ValueError) as e:
            return web.HTTPForbidden(
                text=json.dumps(dict(result=False, type="invalid source file", message=str(e)),
                                ensure_ascii=False)
            )

        try:
            if target_file.exists():
                raise ValueError(f"Already exists path: {target_file}")

            target = amul.find_format(target_file, target_format)
        except (LoaderNoneMatched, ValueError) as e:
            return web.HTTPForbidden(
                text=json.dumps(dict(result=False, type="invalid target file", message=str(e)),
                                ensure_ascii=False)
            )

        try:
            dimension = source.level.dimensions[0]
            selection = source.level.bounds(dimension)
            target.create_and_open(target_platform, target_version, selection, False)

            proc = await amul.copy_chunks(source, target)

            await proc.wait()

        except Exception as e:
            try:
                target.close()
                os.remove(target_file)
            except (Exception,):
                pass

            return web.HTTPForbidden(
                text=json.dumps(dict(result=False, type="process error", message=str(e)), ensure_ascii=False),
                reason=f"Failed to conversion: {e}"
            )
        finally:
            target.close()
            amul.unload_file(source)

        return web.HTTPOk(text=json.dumps(dict(result=True)))

    app.add_routes(routers)
    return app


if __name__ == '__main__':
    web.run_app(create_server_app())
