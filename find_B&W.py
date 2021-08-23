import os
import sys
import glob
from PIL import Image, ImageStat
import PIL

dirname = '/data/cy_strap/train'
outname = '/data/cy_strap/real_BW_train'

def find_black_white(file):
    ind_image = Image.open(file)
    bands = ind_image.getbands()
    if bands == ('R','G','B') or bands== ('R','G','B','A'):
        resized = ind_image.resize((40,40))
        mean = ImageStat.Stat(resized).mean[:3]
        if mean[0]==mean[1] and mean[1]==mean[2]: 
            same = 0
            pix = 0
            for pixel in resized.getdata():
                pix+=1
                if (pixel.count(pixel[0]) == len(pixel)): same+=1
            if pix==same:
                return 100
                
# put all completely black and white images into /real_BW_train
imgs = glob.glob(f'{dirname}/*')
count = 0
for img in imgs:
    n = find_black_white(img)
    if n == 100: 
        temp = img.split('/')[-1]
        createpath = os.path.join(outname, temp)
        os.symlink(img, createpath)
        count+=1
print(count)

# put only 1000 black and white images from /real_BW_train into /BW_train 
a = '/data/cy_strap/real_BW_train'
b = '/data/cy_strap/BW_train'
c = '/data/cy_strap/train'

real = glob.glob(f'{a}/*')
export = real[:1000]
print(len(export))
for file in export:
    temp = file.split('/')[-1]
    orig_path = os.path.join(c, temp)
    out_path = os.path.join(b, temp)
    os.symlink(orig_path, out_path)
