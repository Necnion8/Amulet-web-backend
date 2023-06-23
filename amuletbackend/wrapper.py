import asyncio
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

from amulet.api.level import World, Structure
from amulet.api.wrapper import FormatWrapper

if TYPE_CHECKING:
    from amuletbackend.server import AmuletServer

__all__ = ["AmuletLevel", "AmuletProcess", "AmuletChunkCopyProcess"]
log = getLogger(__name__)


class AmuletLevel(object):
    def __init__(self, server: "AmuletServer", level: World | Structure, path: Path, path_key: str):
        self._mgr = server
        self.level = level
        self.path = path
        self.key = path_key
        self._uses = set()  # type: set[object]

    @property
    def is_used(self):
        return bool(self._uses)

    def add_use(self, obj: object):
        self._uses.add(obj)
        self._mgr._on_used(self)

    def remove_use(self, obj: object):
        self._uses.discard(obj)
        if not self._uses:
            self._mgr._on_unused(self)

    def close(self):
        self.level.close()


class AmuletProcess:
    def progress(self) -> float | None:
        raise NotImplementedError

    def info(self) -> dict:
        raise NotImplementedError


class AmuletChunkCopyProcess(AmuletProcess):
    def __init__(self, level: AmuletLevel, target: FormatWrapper):
        self.level = level
        self.source = level.level
        self.target = target
        #
        self._progress = None
        self._interrupted = False
        self._task = None  # type: asyncio.Task | None
        #
        self.source_dim = level.level.dimensions[0]
        self.source_selection = level.level.bounds(self.source_dim)
        self.target_dim = target.dimensions[0]

    def progress(self) -> float | None:
        return self._progress

    def info(self) -> dict:
        return dict(
            path=str(self.level.path.as_posix()),
            sourceClass=type(self.source).__name__,
            sourceDimension=self.source_dim,
            sourceSelectionMin=self.source_selection.min_array.astype(int).tolist(),
            sourceSelectionMax=self.source_selection.max_array.astype(int).tolist(),
            targetClass=type(self.target).__name__,
            targetDimension=self.target_dim,
        )

    def _run(self):
        level = self.source
        source_dim, source_selection, target, target_dim = (
            self.source_dim, self.source_selection, self.target, self.target_dim
        )

        self._progress = 0
        chunks = source_selection.chunk_locations()
        for idx, (cx, cz) in enumerate(chunks):
            if self._interrupted:
                raise InterruptedError()
            chunk = level.get_chunk(cx, cz, source_dim)
            target.commit_chunk(chunk, target_dim)
            self._progress = idx / len(chunks)

        target.save()
        self._progress = 1

    async def start(self):
        if self._task is None:
            async def _start():
                log.info("Starting chunk copy: %s", self.level.path)
                try:
                    await asyncio.get_running_loop().run_in_executor(None, self._run)
                except InterruptedError:
                    log.warning("Interrupted chunk copy process: %s", self.level.path)
                    raise
                except Exception as e:
                    log.error("Exception in chunk copy: %s", self.level.path, exc_info=e)
                    raise
                else:
                    log.info("Completed chunk copy: %s", self.level.path)
                finally:
                    self._task = None
            self._task = asyncio.create_task(_start())

    async def cancel(self):
        if self._task is None:
            return
        self._interrupted = True
        self._task.cancel()
        try:
            await self.wait()
        except (Exception,):
            pass

    async def wait(self):
        if self._task:
            await asyncio.shield(self._task)
