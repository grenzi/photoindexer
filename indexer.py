import subprocess
import re
import os
import json
from enum import Enum
from datetime import datetime,date
import logging
import pathlib
from tqdm import tqdm
import hashlib as hash
import exifread
from PIL import Image
from datastructures import Volume, IndexedFile,load_index_if_exists, save_index
#from iptcinfo3 import IPTCInfo

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def parse_wmic_output(text):
    result = []
    # remove empty lines
    lines = [s for s in text.splitlines() if s.strip()]
    # No Instance(s) Available
    if len(lines) == 0:
        return result
    header_line = lines[0]
    # Find headers and their positions
    headers = re.findall('\S+\s+|\S$', header_line)
    pos = [0]
    for header in headers:
        pos.append(pos[-1] + len(header))
    for i in range(len(headers)):
        headers[i] = headers[i].strip()
    # Parse each entries
    for r in range(1, len(lines)):
        row = {}
        for i in range(len(pos)-1):
            row[headers[i]] = lines[r][pos[i]:pos[i+1]].strip()
        result.append(row)
    return result

def get_volume_information(drive_letter, base_path):
    #wmic logicaldisk where "name='e:'" get Description,DeviceID,FileSystem,FreeSpace,Size,SystemName,VolumeName,VolumeSerialNumber   
    args = """wmic logicaldisk where "name='current_drive_letter'" get Description,DeviceID,FileSystem,FreeSpace,Size,SystemName,VolumeName,VolumeSerialNumber"""  
    process = subprocess.check_output(args.replace('current_drive_letter', drive_letter))
    o = process.strip().decode()
    s = parse_wmic_output(o)[0] 
    s['BasePath']=base_path
    return s

def add_volume(index, volume_info):
    volume_node=list([n for n in index if 
        n.VolumeSerialNumber==volume_info['VolumeSerialNumber'] and
        n.BasePath == volume_info['BasePath'] ])

    if len(volume_node)>0:
        ret=volume_node[0]
    else:
        ret = Volume([],**volume_info)    
        index.append(ret)
    return ret

def find_files(start_dir):
    ret = []
    for subdir, dirs, files in os.walk(start_dir):        
        logger.info(f'Processing {subdir}')
        for file in files:
            ret.append(os.path.join(subdir, file))
    return ret

def hash_file(filepath):    
    BLOCKSIZE = 65536
    sha = hash.sha256()
    with open(filepath, 'rb') as fp:
        file_buffer = fp.read(BLOCKSIZE)
        while len(file_buffer) > 0:
            sha.update(file_buffer)
            file_buffer = fp.read(BLOCKSIZE)        
    return (sha.hexdigest())

def file_handler(volume,filepath, thumb_dir):
    logger.debug(f'...processing {filepath}')
    stat = os.stat(filepath)
    indexed_file = IndexedFile(
        *os.path.split(filepath),
        stat.st_ino,
        stat.st_dev,
        stat.st_size,
        datetime.fromtimestamp(stat.st_atime),
        datetime.fromtimestamp(stat.st_mtime),
        datetime.fromtimestamp(stat.st_ctime),
        )
    indexed_file.SHA256 = hash_file(filepath)

    #get exif tags
    with open(filepath, 'rb') as f:
        exif=exifread.process_file(f,details=False)
    indexed_file.EXIF = {}
    for k in [t for t in sorted(exif.keys()) if t not in (
        'JPEGThumbnail', 'TIFFThumbnail', 'Filename','EXIF MakerNote',
        'Image IPTC/NAA','Image InterColorProfile')]:
            indexed_file.EXIF[k]=str(exif[k])

    #create thumbnail
    outfile = os.path.join(thumb_dir,indexed_file.SHA256+'.jpeg')
    if os.path.exists(outfile) == False:
        try:
            size=300,300
            im = Image.open(filepath)
            im.thumbnail(size, Image.ANTIALIAS)
            im.save(outfile, "JPEG")        
        except:
            pass

    #act based on file extension    
    file_extension = pathlib.Path(filepath).suffix.lower()

    #tbd - need to handle the  IPTC/NAA tags? 
    # https://iptc.org/standards/photo-metadata/
    #
    # if (exif.get("Image IPTC/NAA", None)) != None:
    #     info=IPTCInfo(filepath)
    #     for k in info    
    volume.files.append(indexed_file)
    

###############################################################################
image_dir = r'E:\code\laird\images'
index_dir = os.path.join(os.getcwd(), 'index')
thumb_dir = r'e:\Code\laird\index\thumbs'

current_drive_letter = os.path.splitdrive(os.getcwd())[0]

logger.info('getting disk volume information')
volume_info = get_volume_information(current_drive_letter, image_dir)

logger.info('loading / creating index file')
index_file_path = os.path.join(index_dir, f"idx_{volume_info['VolumeSerialNumber']}.json")
index = load_index_if_exists(index_file_path)
volume = add_volume(index, volume_info)

logger.info('identifying files')
files_to_index = find_files(image_dir)

logger.info('processing files')
for file in tqdm(files_to_index):
    file_handler(volume, file, thumb_dir)

logger.info('saving output')
save_index(index, index_file_path)
