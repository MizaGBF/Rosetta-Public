from __future__ import annotations
import disnake
from typing import Generator, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
import os
import io
import shutil
from contextlib import contextmanager

# ----------------------------------------------------------------------
# File Component
# ----------------------------------------------------------------------
# Let your copy or delete local files
# ----------------------------------------------------------------------


class File():
    __slots__ = ("bot")

    def __init__(self : File, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    def init(self) -> None:
        pass

    """rm()
    Delete a file from the disk

    Parameters
    ----------
    filename: File path
    """
    def rm(self : File, filename : str) -> None:
        try:
            os.remove(filename)
        except:
            pass

    """cpy()
    Copy a file on the disk

    Parameters
    ----------
    src: Source File path
    dst: Destination File path
    """
    def cpy(self : File, src : str, dst : str) -> None:
        try:
            shutil.copyfile(src, dst)
        except:
            pass

    """mv()
    Move a file on the disk

    Parameters
    ----------
    src: Source File path
    dst: Destination File path
    """
    def mv(self : File, src : str, dst : str) -> None:
        try:
            if self.exist(src):
                if self.exist(dst):
                    self.rm(dst) # delete destination beforehand, to be sure
                shutil.move(src, dst)
        except:
            pass

    """exist()
    Check whatever the file exists

    Parameters
    ----------
    path: Path to the target

    Returns
    ----------
    bool: True if it exists, False otherwise
    """
    def exist(self : File, path : str) -> bool:
        try:
            return os.path.isfile(path)
        except:
            return False

    """discord()
    Context Manager for disnake.File objects
    """
    @contextmanager
    def discord(
        self : File,
        fp : io.BufferedIOBase,
        filename : str|None = None,
        spoiler : bool = False,
        description : str|None = None
    ) -> Generator[disnake.File, None, None]:
        df : disnake.File = disnake.File(fp=fp, filename=filename, spoiler=spoiler, description=description)
        try:
            yield df
        finally:
            df.close()
