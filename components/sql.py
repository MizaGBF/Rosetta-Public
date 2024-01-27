import asyncio
from typing import Optional, Type, TYPE_CHECKING
import traceback
if TYPE_CHECKING: from ..bot import DiscordBot
import sqlite3

# ----------------------------------------------------------------------------------------------------------------
# SQL Component
# ----------------------------------------------------------------------------------------------------------------
# Manage Database objects
# Database objects are simple wrapper over a sqlite3 connection and cursor with a multithreading protection
# It's made in a way to simplify the way it was used in the previous bot versions
# ----------------------------------------------------------------------------------------------------------------

class Database():
    def __init__(self, filename : str) -> None:
        self.filename = filename
        self.conn = None
        self.cursor = None
        self.lock = asyncio.Lock()

    async def __aenter__(self) -> Optional[sqlite3.Cursor]:
        try:
            await self.lock.acquire()
            self.conn = sqlite3.connect(self.filename)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA locking_mode = exclusive")
            self.cursor.execute("PRAGMA synchronous = normal")
            self.cursor.execute("PRAGMA journal_mode = OFF")
            return self.cursor
        except:
            self.lock.release()
            return None
    
    async def __aexit__(self, exc_type : Optional[Type[BaseException]], exc_val : Optional[BaseException], exc_tb : Optional[traceback]) -> Optional[bool]:
        try: self.cursor.close()
        except: pass
        try: self.conn.close()
        except: pass
        self.conn = None
        self.cursor = None
        self.lock.release()

class SQL():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.file = None
        self.db = {}
        self.lock = asyncio.Lock()

    def init(self) -> None:
        pass

    """remove()
    Remove the Database object from the cache
    
    Parameters
    ----------
    filename: SQL file name
    """
    async def remove(self, filename : str) -> None:
        async with self.lock:
            if filename in self.db:
                db = self.db[filename]
                async with db.lock:
                    self.db.pop(filename)

    """remove_list()
    Remove the Database object from the cache
    
    Parameters
    ----------
    filename: SQL file name
    """
    async def remove_list(self, filenames : list) -> None:
        async with self.lock:
            for f in filenames:
                if f in self.db:
                    db = self.db[f]
                    async with db.lock:
                        self.db.pop(f)

    """add()
    Add a new Database object to the cache (Remove the previous one if any).
    The file must exist to avoid future errors
    
    Parameters
    ----------
    filename: SQL file name
    
    Returns
    --------
    Database: The new Database object. None if the file doesn't exist
    """
    async def add(self, filename : str) -> Optional[Database]:
        async with self.lock:
            if self.bot.file.exist(filename):
                    self.db[filename] = Database(filename)
                    return self.db[filename]
            else:
                return None

    """get()
    Retrieve a Database object from the cache
    
    Parameters
    ----------
    filename: SQL file name
    
    Returns
    --------
    Database: The Database object. None if it doesn't exist
    """
    async def get(self, filename : str) -> Optional[Database]:
        async with self.lock:
            return self.db.get(filename, None)