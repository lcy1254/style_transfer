n = 37
# need to start from 14

# for some reason, cannot run stylize_saveHdf5 multiple times in one script 
import os, glob, json 
import time
import numpy as np
import pandas as pd
import h5py 
from PIL import Image 
import random 
from random import shuffle 
import copy 
import pickle 
from math import ceil 
import matplotlib.pyplot as plt
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True 

from stylize_datasets.stylize_saveHdf5_wilds import stylize_saveHdf5

data_dir = '/media/dnr/data_crypt/cy_strap/camelyon17_v1.0/patches/'
main_dir = '/media/dnr/data_crypt/cy_strap/train_folders' 
main_outdir = '/media/dnr/data_crypt/cy_strap/output/'
folders = glob.glob(f'{main_dir}/*/')
print(len(folders))
'''
for folder in folders:
    style_dir = folder
    type = str(folder.split('/')[-2]) + '_256_1024_256_alpha10.hdf5'
    out_path = os.path.join(main_outdir, type) 
    error = stylize_saveHdf5(data_dir=data_dir, style_dir=style_dir, out_path=out_path, alpha=1., save_size=256, content_size=1024, style_size=256)
    print(error)
'''

style_dir = folders[n]
print(style_dir)
type = str(folders[n].split('/')[-2]) + '_256_1024_256_alpha10.hdf5'
out_path = os.path.join(main_outdir, type)
print(out_path)
error = stylize_saveHdf5(data_dir=data_dir, style_dir=style_dir, out_path=out_path, alpha=1., save_size=256, content_size=1024, style_size=256)
print(error)
