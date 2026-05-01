
import os
from dotenv import load_dotenv
from pprint import pprint
from pcloud import PyCloud # https://github.com/tomgross/pcloud
import yaml


load_dotenv(".secrets")

PCLOUD_PW = os.getenv("PCLOUD_PW", None)
PCLOUD_USER = os.getenv("PCLOUD_USER", None)

assert PCLOUD_USER and PCLOUD_PW, "PCLOUD credentials missing"

    
# read config
with open('config.yaml', "r") as f:
    CONFIG = yaml.safe_load(f)

# create local directory if not exists
if not os.path.exists(CONFIG['pcloud']['local_path']):
    os.makedirs(CONFIG['pcloud']['local_path'])

# login
pc = PyCloud(PCLOUD_USER, PCLOUD_PW, endpoint="eapi")
# get folder list
folderlist = pc.listfolder(folderid=0)
pprint(folderlist)

content = pc.listfolder(path=CONFIG['pcloud']['remote_path'])
for f in content['metadata']['contents']:
    print(f"{f['name']:40}  {f['folderid']:10}")

# folder
folder_name = f"{CONFIG['pcloud']['remote_path']}/Samsung SM-M356B"
content = pc.listfolder(path=folder_name)
# loop over first 10 files
for f in content['metadata']['contents'][30:100]:
    print(f" download {f['name']:40} {f['fileid']:10}")
    # skip if not image
    if not f['name'].lower().endswith(('.png', '.jpg', '.jpeg')):
        print("  -> skipping, not an image")
        continue
    # download
    raw_file = pc.file_download(fileid=f['fileid'])
    # write to file
    local_file_path = os.path.join(CONFIG['pcloud']['local_path'], f['name'])
    with open(local_file_path, "wb") as f:
        f.write(raw_file)

print(f"Found {len(content['metadata']['contents'])} files in {folder_name}:")
