import os
import json
from enum import Enum
from datetime import datetime,date
import logging
import pathlib
from tqdm import tqdm
from datastructures import Volume, IndexedFile,load_index_if_exists, save_index
from os import listdir
from os.path import isfile, join
import itertools
import csv

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

###############################################################################
index_dir = os.path.join(os.getcwd(), 'index')

logger.info('finding index files')
indexfiles = list([f for f in listdir(index_dir) if isfile(join(index_dir, f)) and f[-4:]=='json'])

columns = ['VolumeName', 'VolumeSerialNumber', 'Directory', 'Name', 'InodeNumber', 'Modified On', 'Created On', 'SHA256']
exif_columns=set()

logger.info('parsing index files')
#Pass 1 = collect keys
for index_file in indexfiles:
    index = load_index_if_exists(os.path.join(index_dir, index_file))
    for vol in index:
        for ixf in vol.files:
            if ixf.EXIF is not None:
                for i in ixf.EXIF.keys():
                    exif_columns.add(i)

logger.info('writing csv')
#Pass 2 = write header
with open(os.path.join(os.getcwd(), 'index.csv'), mode='w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(columns+list(exif_columns))
    #and now rows
    for index_file in indexfiles:
        index = load_index_if_exists(os.path.join(index_dir, index_file))
        for vol in index:
            for ixf in vol.files:
                row = [
                    vol.VolumeName,
                    vol.VolumeSerialNumber,
                    ixf.Directory,
                    ixf.Name,
                    ixf.st_ino,
                    ixf.st_mtime.strftime("%c"),
                    ixf.st_ctime.strftime("%c"),
                    ixf.SHA256
                ]
                for ec in exif_columns:
                    row.append(ixf.EXIF.get(ec, None))
                writer.writerow(row)