from dataclasses import dataclass,field
from datetime import datetime,date
from dataclasses_json import dataclass_json
from typing import List,Any,Dict
import os
import logging

logger = logging.getLogger()

@dataclass_json
@dataclass
class IndexedFile:
    Directory: str=None
    Name: str=None
    #inode number
    st_ino: int=None
    #device inode
    st_dev: int=None
    #size in bytes
    st_size: int=None
    #last access time
    st_atime: datetime=None
    #last modified time
    st_mtime: datetime=None
    #created time
    st_ctime: datetime=None
    SHA256:str=None
    EXIF: Dict[str,str]=None
    NodeType:str='FILE'

@dataclass_json
@dataclass
class Volume:
    files: List[IndexedFile]
    Description: str
    DeviceID: str
    FileSystem: str
    FreeSpace: str
    Size: str
    SystemName: str
    VolumeName: str
    VolumeSerialNumber: str
    BasePath: str
    NodeType: str='Volume'

def load_index_if_exists(filepath):
    if os.path.exists(filepath):
        data = open(filepath, mode='r', encoding='utf-8').read()
        return Volume.schema().loads(data, many=True)
    else:
        logger.warning(f'{filepath} does not exist. creating new index')
        return []

def save_index(volumes, filepath):
    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(Volume.schema().dumps(volumes, many=True))
