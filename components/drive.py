from typing import Union, Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from datetime import datetime
import io
import gzip
import lzma
import os

# ----------------------------------------------------------------------------------------------------------------
# Drive Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages the save data file (save.json) over Google Drive
# It also lets you send and retrieve files from Google Drive for whatever application you might need
# ----------------------------------------------------------------------------------------------------------------

class Drive():
    ZIP_CHUNK = 8192
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot
        self.debug = bot.debug_mode or bot.test_mode
        self.gauth = None
        self.gdrive = None
        try:
            # Set GoogleAuth with service-secrets.json
            self.gauth = GoogleAuth(settings={
                        "client_config_backend": "service",
                        "service_config": {
                            "client_json_file_path": "service-secrets.json",
                        }
                    })
            # Authenticate
            self.gauth.ServiceAuth()
            self.gdrive = GoogleDrive(self.gauth)
        except OSError as e:
            self.gauth = None
            self.gdrive = None
            self.bot.logger.pushError("[DRIVE] Failed to initialize Drive component, couldn't open service-secrets.json:", e, send_to_discord=False)
            raise e
        except Exception as e:
            self.gauth = None
            self.gdrive = None
            self.bot.logger.pushError("[DRIVE] Failed to initialize Drive component:", e, send_to_discord=False)
            raise e
        # Raise exceptions in case of errors

    def init(self) -> None:
        pass

    """decompressJSON_gzip()
    Decompress the given byte array (which must be valid compressed gzip data) and return the decoded text (utf-8).
    Legacy code for compatibility with very old MizaBOT saves. It shoudn't be needed anymore.
    
    Parameters
    --------
    inputBytes: data to decompress
    
    Returns
    --------
    str: Decompressed string
    """
    def decompressJSON_gzip(self, inputBytes : Union[bytes, str]) -> Optional[str]:
        with io.BytesIO() as bio:
            with io.BytesIO(inputBytes) as stream:
                decompressor = gzip.GzipFile(fileobj=stream, mode='r')
                while True:
                    chunk = decompressor.read(self.ZIP_CHUNK) # decompress the next chunk
                    if not chunk: # we reached EOF
                        decompressor.close()
                        bio.seek(0) # go back to BytesIO beginning
                        return bio.read().decode("utf-8") # read its content, decode and return
                    # write decompressed chunk to BytesIO
                    bio.write(chunk)
                return None

    """decompressJSON()
    Decompress the given byte array (which must be valid compressed lzma data) and return the decoded text (utf-8).
    
    Parameters
    --------
    inputBytes: data to decompress
    
    Returns
    --------
    str: Decompressed string
    """
    def decompressJSON(self, inputBytes : Union[bytes, str]) -> Optional[str]:
        with io.BytesIO() as bio:
            with io.BytesIO(inputBytes) as stream:
                decompressor = lzma.LZMADecompressor()
                while not decompressor.eof:
                    chunk = decompressor.decompress(stream.read(self.ZIP_CHUNK), max_length=self.ZIP_CHUNK) # decompress the next chunk
                    if decompressor.eof: # we reached EOF
                        if len(chunk) > 0: bio.write(chunk)
                        bio.seek(0) # go back to BytesIO beginning
                        return bio.read().decode("utf-8") # read its content, decode and return
                    # write decompressed chunk to BytesIO
                    bio.write(chunk)
                return None

    """compressJSON()
    Read the given string, encode it in utf-8, compress the data and return it as a byte array.
    json.dumps() must have been used before this function.
    
    Parameters
    --------
    inputString: data to compress
    
    Returns
    --------
    bytes: Compressed string
    """
    def compressJSON(self, inputString : str) -> bytes:
        with io.BytesIO() as bio:
            bio.write(inputString.encode("utf-8")) # set binary content
            bio.seek(0) # go to beginning
            buffers = []
            compressor = lzma.LZMACompressor()
            while True:
                chunk = bio.read(self.ZIP_CHUNK) # read a chunk
                if not chunk: # EOF
                    buffers.append(compressor.flush()) # flush to finish
                    return b"".join(buffers) # return joined compressed result
                buffers.append(compressor.compress(chunk)) # add compressed chunk

    """load()
    Download save.json

    --------
    bool: True if success, False if failure
    """
    def load(self) -> bool:
        try:
            file_list = self.gdrive.ListFile({'q': "'" + self.bot.data.config['tokens']['drive'] + "' in parents and trashed=false"}).GetList() # get the file list in our folder
            # search the save file
            for s in file_list: # iterate until we find a compressed save
                match s['title']:
                    case "save.gzip": # legacy compatibility for .gzip
                        s.GetContentFile(s['title']) # download
                        with open("save.gzip", "rb") as stream: # read file
                            with open("save.json", "w") as out: # and uncompress
                                out.write(self.decompressJSON_gzip(stream.read()))
                        os.remove("save.gzip") # delete compressed version
                        return True
                    case "save.lzma":
                        s.GetContentFile(s['title']) # download
                        with open("save.lzma", "rb") as stream: # read file
                            with open("save.json", "w") as out: # and uncompress
                                out.write(self.decompressJSON(stream.read()))
                        os.remove("save.lzma") # delete compressed version
                        return True
            # fallback, legacy compatibility for uncompressed.json
            for s in file_list:
                if s['title'] == "save.json":
                    s.GetContentFile(s['title']) # download
                    return True
            # not found
            return False
        except Exception as e:
            self.bot.logger.pushError("[DRIVE] Failed to load 'save.json':", e, send_to_discord=False)
            return False

    """save()
    Upload save.json to a specified folder

    Parameters
    ----------
    data: Save data

    Returns
    --------
    bool: True if success, False if failure, None if debug
    """
    def save(self, data : dict) -> Optional[bool]: # write data as save.json to the folder id in tokens
        if self.debug: return None
        try:
            # get file list
            file_list = self.gdrive.ListFile({'q': "'" + self.bot.data.config['tokens']['drive'] + "' in parents and trashed=false"}).GetList()
            if len(file_list) > 9: # delete if we have too many backups
                for f in file_list:
                    if f['title'].startswith('backup'):
                        f.Delete()
            # list the previous save(s)
            prev = [f for f in file_list if f['title'] in ["save.json", "save.gzip", "save.lzma"]]
            # compress the one passed as a parameter
            cdata = self.compressJSON(data)
            # create file
            s = self.gdrive.CreateFile({'title':'save.lzma', 'mimeType':'application/x-lzma', "parents": [{"kind": "drive#file", "id": self.bot.data.config['tokens']['drive']}]})
            with io.BytesIO(cdata) as stream:
                s.content = stream
                s.Upload() # upload
            # rename the previous save(s) to backup
            for f in prev:
                f['title'] = "backup_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "." + f['title'].split(".")[-1]
                f.Upload()
            return True
        except Exception as e:
            self.bot.logger.pushError("[DRIVE] Failed to upload 'save.json':", e, send_to_discord=False)
            return False

    """saveDiskFile()
    Upload a file to a specified folder
    
    Parameters
    ----------
    target: File to save
    mile: File mime type
    name: File name
    folder: Google Drive Folder ID
    
    Returns
    --------
    bool: True if success, False if failure, None if debug
    """
    def saveDiskFile(self, target : str, mime : str, name : str, folder : str) -> Optional[bool]:
        if self.debug: return None
        try:
            s = self.gdrive.CreateFile({'title':name, 'mimeType':mime, "parents": [{"kind": "drive#file", "id": folder}]})
            with open(target, "rb") as stream: # open file
                s.content = stream
                s.Upload() # and upload
            return True
        except Exception as e:
            self.bot.logger.pushError("[DRIVE] Failed to upload file '{}':", e, send_to_discord=False)
            return False

    """overwriteFile()
    Upload a file to a specified folder, overwrite an existing file if it exists
    
    Parameters
    ----------
    target: File to save
    mile: File mime type
    name: File name
    folder: Google Drive Folder ID
    
    Returns
    --------
    bool: True if success, False if failure, None if debug
    """
    def overwriteFile(self, target : str, mime : str, name : str, folder : str) -> Optional[bool]:
        if self.debug: return None
        try:
            # get file list
            file_list = self.gdrive.ListFile({'q': "'" + folder + "' in parents and trashed=false"}).GetList()
            for s in file_list:
                if s['title'] == name: # if our file is found
                    with open(target, "rb") as stream: # update it with our local file content
                        s.content = stream
                        s.Upload()
                    return True
        except Exception as e:
            self.bot.logger.pushError("[DRIVE] Failed to overwrite file '{}':", e, send_to_discord=False)
            return False
        # not found, we do a normal upload
        return self.saveDiskFile(target, mime, name, folder)

    """mvFile()
    Rename a file in a folder
    
    Parameters
    ----------
    name: File name
    folder: Google Drive Folder ID
    name: New File name
    
    Returns
    --------
    bool: True if success, False if failure, None if debug
    """
    def mvFile(self, name : str, folder : str, new : str) -> Optional[bool]:
        if self.debug: return None
        try:
            # get file list
            file_list = self.gdrive.ListFile({'q': "'" + folder + "' in parents and trashed=false"}).GetList()
            for s in file_list:
                if s['title'] == name: # the file is found
                    s['title'] = new # change the name
                    s.Upload() # and update
                    return True
            return False
        except Exception as e:
            self.bot.logger.pushError("[DRIVE] Failed to move file '{}':", e, send_to_discord=False)
            return False

    """dlFile()
    Download a file from a folder
    Parameters
    ----------
    name: File name
    folder: Google Drive Folder ID
    destination: String, file name to save the file to
    Returns
    --------
    bool: True if success, False if failure, None if doesn't exist
    """
    def dlFile(self, name : str, folder : str, destination : Optional[str] = None)-> Optional[bool]:
        try:
            # get file list
            file_list = self.gdrive.ListFile({'q': "'" + folder + "' in parents and trashed=false"}).GetList() # get the file list in our folder
            for s in file_list:
                if s['title'] == name: # our file is found
                    s.GetContentFile(s['title'] if destination is None else destination) # download it
                    return True
            return None
        except Exception as e:
            self.bot.logger.pushError("[DRIVE] Failed to download file '{}':", e, send_to_discord=False)
            return False