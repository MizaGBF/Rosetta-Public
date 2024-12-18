from __future__ import annotations
import asyncio
from typing import Type, TYPE_CHECKING
import traceback
if TYPE_CHECKING:
    from ..bot import DiscordBot
import sqlite3

# ----------------------------------------------------------------------------------------------------------------
# SQL Component
# ----------------------------------------------------------------------------------------------------------------
# Manage Database objects
# Database objects are simple wrapper over a sqlite3 connection and cursor with a multithreading protection
# It's made in a way to simplify the way it was used in the previous bot versions
# ----------------------------------------------------------------------------------------------------------------

class Database():
    def __init__(self : Database, filename : str) -> None:
        self.filename : str = filename
        self.conn :  sqlite3.Connection|None = None # connection
        self.cursor : sqlite3.Cursor|None = None # cursor
        self.lock : asyncio.Lock = asyncio.Lock()

    async def __aenter__(self : Database) -> sqlite3.Cursor|None: # opening
        try:
            await self.lock.acquire() # lock
            # open handles
            self.conn = sqlite3.connect(self.filename)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA locking_mode = exclusive")
            self.cursor.execute("PRAGMA synchronous = normal")
            self.cursor.execute("PRAGMA journal_mode = OFF")
            # return cursor
            return self.cursor
        except:
            self.lock.release() # error, unlock
            return None
    
    async def __aexit__(self : Database, exc_type : Type[BaseException]|None, exc_val : BaseException|None, exc_tb : traceback|None) -> bool|None: # closing
        # close the handles
        try: self.cursor.close()
        except: pass
        try: self.conn.close()
        except: pass
        self.conn = None
        self.cursor = None
        # unlock
        self.lock.release()

class SQL():
    def __init__(self : SQL, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.db : dict[str, Database] = {} # sql files
        self.lock : asyncio.Lock = asyncio.Lock() # global lock

    def init(self : SQL) -> None:
        pass

    """remove()
    Remove the Database object from the cache
    
    Parameters
    ----------
    filename: SQL file name
    """
    async def remove(self : SQL, filename : str) -> None:
        async with self.lock:
            if filename in self.db: # remove file if in memory
                db : Database = self.db[filename]
                async with db.lock:
                    self.db.pop(filename)

    """remove_list()
    Remove the Database object from the cache
    
    Parameters
    ----------
    filename: SQL file name
    """
    async def remove_list(self : SQL, filenames : list[str]) -> None:
        async with self.lock:
            f : str
            for f in filenames: # remove all given files if they are in memory
                if f in self.db:
                    db : Database = self.db[f]
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
    async def add(self, filename : str) -> Database|None:
        async with self.lock:
            if self.bot.file.exist(filename): # create Database instance in memory if file exists
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
    async def get(self, filename : str) -> Database|None:
        async with self.lock: # return Database instance if it exists
            return self.db.get(filename, None)