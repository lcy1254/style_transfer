import sys, os, glob
sys.path.append(os.path.dirname(__file__))

import argparse
from function import adaptive_instance_normalization
import net
from pathlib import Path
from PIL import Image
import random
import torch
import torch.nn as nn
import torchvision.transforms
from torchvision.utils import save_image
from tqdm import tqdm

import numpy as np
import tables

def input_transform(size, crop):
    transform_list = []
    if size != 0:
        transform_list.append(torchvision.transforms.Resize(size))
    if crop != 0:
        transform_list.append(torchvision.transforms.CenterCrop(crop))
    transform_list.append(torchvision.transforms.ToTensor())
    transform = torchvision.transforms.Compose(transform_list)
    return transform

def style_transfer(vgg, decoder, content, style, alpha=1.0):
    assert (0.0 <= alpha <= 1.0)
    content_f = vgg(content)
    style_f = vgg(style)
    feat = adaptive_instance_normalization(content_f, style_f)
    feat = feat * alpha + content_f * (1 - alpha)
    return decoder(feat)

def stylize_saveHdf5(data_dir, style_dir, out_path, alpha=1., save_size=96, content_size=1024, style_size=256):

    # collect style files
    style_dir = Path(style_dir)
    style_dir = style_dir.resolve()
    extensions = ['png', 'jpeg', 'jpg']
    styles = []
    for ext in extensions:
        styles += list(style_dir.rglob('*.' + ext))

    assert len(styles) > 0, 'No images with specified extensions found in style directory' + style_dir
    styles = sorted(styles)
    # print('Found %d style images in %s' % (len(styles), style_dir))

    decoder = net.decoder
    vgg = net.vgg

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    decoder.eval()
    vgg.eval()

    decoder.load_state_dict(torch.load('/home/lcy/style_transfer/stylize_datasets/models/decoder.pth'))
    vgg.load_state_dict(torch.load('/home/lcy/style_transfer/stylize_datasets/models/vgg_normalised.pth'))
    vgg = nn.Sequential(*list(vgg.children())[:31])

    vgg.to(device)
    decoder.to(device)

    crop = 0
    content_tf = input_transform(content_size, crop)
    style_tf = input_transform(style_size, 0)

    hdf5_file = tables.open_file(out_path, mode='w')
    # data_shape = (0, 256, 256, 3)
    data_shape = (0, save_size, save_size, 3)
    img_dtype = tables.UInt8Atom()
    storage = hdf5_file.create_earray(hdf5_file.root, 'img', img_dtype, shape=data_shape)

    # disable decompression bomb errors
    Image.MAX_IMAGE_PIXELS = None

    filenames = []
    error = []
    
    # actual style transfer as in AdaIN

    image_paths = glob.glob(f'{data_dir}*/*.png')
    for idx in range(len(image_paths)):
        try:
            content_img = Image.open(image_paths[idx]).convert('RGB')
            for style_path in random.sample(styles, 1):
                style_img = Image.open(style_path).convert('RGB')

                content = content_tf(content_img)
                style = style_tf(style_img)
                style = style.to(device).unsqueeze(0)
                content = content.to(device).unsqueeze(0)
                with torch.no_grad():
                    output = style_transfer(vgg, decoder, content, style, alpha)
                # output = output.cpu()
                output = output.cpu().squeeze_(0)
                output_img = torchvision.transforms.ToPILImage()(output)
                # output_img = output_img.resize((256, 256), Image.LANCZOS)
                output_img = output_img.resize((save_size, save_size), Image.LANCZOS)
                output = np.array(output_img)

                # output = output.cpu().squeeze_(0).permute(1, 2, 0).numpy()
                storage.append(output[None])

                style_img.close()    
            content_img.close()
            filenames.append(image_paths[idx])

        except Exception as err:
            print(f'Skipping stylization of {image_paths[idx]} due to an error of {err})')
            error.append(idx)

    hdf5_file.create_array(hdf5_file.root, 'filenames', filenames)
    hdf5_file.close()
    return error
