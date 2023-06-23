import asyncio
from logging import getLogger
from pathlib import Path

import amulet
from amulet.api.errors import LoaderNoneMatched
from amulet.api.wrapper import FormatWrapper
from amulet.level.loader import Formats

from amuletbackend.wrapper import AmuletLevel, AmuletProcess, AmuletChunkCopyProcess

log = getLogger(__name__)
__version__ = "1.0.0/230623"


def _path_key_of(path: Path | str):
    if not isinstance(path, Path):
        path = Path(path)
    return path.absolute().as_posix().lower()


async def _async_load_level(server: "AmuletServer", path: Path):
    log.info("Loading level: %s", path)
    try:
        level = await asyncio.get_running_loop().run_in_executor(None, amulet.load_level, str(path))
    except Exception as e:
        log.error("Failed loading level: %s", exc_info=e)
        raise e
    log.info("Loaded level: %s", level)
    return AmuletLevel(server, level, path, _path_key_of(path))


class AmuletServer(object):
    version = __version__

    def __init__(self):
        self._path_of_levels = {}  # type: dict[str, asyncio.Task[AmuletLevel]]
        self.running_processes = set()  # type: set[AmuletProcess]

    @property
    def open_files(self) -> list[asyncio.Task[AmuletLevel]]:
        return list(self._path_of_levels.values())

    async def load_file(self, path: Path) -> AmuletLevel:
        """
        指定されたパスを開き待機します。完了すると :class:`AmuletLevel` を返します。

        既に開いてるパスである場合は開かれているオブジェクトを返します。
        """
        path = path.absolute()
        path_key = _path_key_of(path)
        try:
            task = self._path_of_levels[path_key]
        except KeyError:
            task = asyncio.create_task(_async_load_level(self, path))
            self._path_of_levels[path_key] = task

        return await asyncio.shield(task)

    def _on_used(self, level: AmuletLevel):
        pass

    def _on_unused(self, level: AmuletLevel):
        self.unload_file(level)

    def unload_file(self, entry: AmuletLevel | Path):
        """
        指定された :class:`AmuletLevel` またはファイルのパスの :class:`AmuletLevel` をアンロードします。

        対象がまた使用中である場合は何もしません。

        また、読み込み中の場合は完了後にアンロードを試みます。
        """
        key = entry.key if isinstance(entry, AmuletLevel) else _path_key_of(entry)
        try:
            task = self._path_of_levels[key]
        except KeyError:
            return  # unloaded

        try:
            level = task.result()
            # loaded
        except (Exception,):
            # now loading
            task.add_done_callback(lambda _: self.unload_file(entry))
            return

        if not level.is_used:
            try:
                level.close()
            finally:
                self._path_of_levels.pop(key, None)
                log.info("Unloaded file: %s", level.path)

    @staticmethod
    def find_format(path: Path, format_name: str) -> FormatWrapper:
        for cls in Formats._objects.values():
            if cls.__name__ == format_name:
                return cls(str(path))
        raise LoaderNoneMatched(f"Unknown format: {format_name}")

    async def copy_chunks(self, source: AmuletLevel, target: FormatWrapper) -> AmuletChunkCopyProcess:
        """
        指定されたソースのチャンクをターゲットへコピーを開始し、:class:`AmuletChunkCopyProcess` を返します。

        :func:`AmuletChunkCopyProcess.wait` で完了を待機することができます。
        """
        proc = AmuletChunkCopyProcess(source, target)
        self.running_processes.add(proc)
        source.add_use(proc)
        await proc.start()
        task = asyncio.get_running_loop().create_task(proc.wait())
        task.add_done_callback(lambda _: self.running_processes.discard(proc))
        return proc
