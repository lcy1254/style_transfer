import os
import sys
import random
import glob
import shutil
import csv 

'----------------------------------------------------'

# generate filenames csv files by running filename.py
# path to 'genre_filename.csv' file
genrefilenames = 'genre_filename.csv'
# path to 'style_filename.csv' file
stylefilenames = 'style_filename.csv'

# path to 'genre-count.csv' file
genrepath = 'genre-count.csv'
# path to 'style-count.csv' file
stylepath = 'style-count.csv'

# path to main directory in which to create genre/style specific folders eg. '/media/dnr/data_crypt/cy_strap/train_folders'
dirname = ''
# path to directory where images are held eg. '/media/dnr/data_crypt/cy_strap/train'
sourcedir = ''

n = 1000

'----------------------------------------------------'

genres = []
styles = []

dictgenres = {}
dictstyles = {}

# get list of genres/styles that have number of images equal to or greater than n
with open(genrepath, 'r') as csvFile:
    csvReader = csv.reader(csvFile)
    header = next(csvReader)
    for row in csvReader:
        rowData = {key: row[idx] for idx, key in enumerate(header)}
        try:
            tempcount = rowData['COUNT']
            tempgenre = rowData['GENRE']
            if tempcount >= n:
                genres.append(tempgenre)
        except (ValueError, AttributeError):
            print('Failed to read data from %s' %(row))
            
with open(stylepath, 'r') as csvFile:
    csvReader = csv.reader(csvFile)
    header = next(csvReader)
    for row in csvReader:
        rowData = {key: row[idx] for idx, key in enumerate(header)}
        try:
            tempcount = rowData['COUNT']
            tempstyle = rowData['STYLE']
            if tempcount >= n:
                styles.append(tempstyle)
        except (ValueError, AttributeError):
            print('Failed to read data from %s' %(row))
            
# exclude blank ('')

if '' in genres:
    genres.remove('')
if '' in styles:
    styles.remove('')

# load random n filenames for each genre/style with number of files greater than n

with open(genrefilenames, 'r') as csvFile:
    csvReader = csv.reader(csvFile)
    header = next(csvReader)
    for row in csvReader:
        rowData = {key: row[idx] for idx, key in enumerate(header)}
        if rowData['GENRE'] in genres:
            tempgenre = rowData['GENRE']
            temp = rowData['FILENAMES']
            templist = temp.strip("]['").split("', '")
            templist2 = random.sample(templist, n)
            dictgenres[tempgenre] = templist2

with open(stylefilenames, 'r') as csvFile:
    csvReader = csv.reader(csvFile)
    header = next(csvReader)
    for row in csvReader:
        rowData = {key: row[idx] for idx, key in enumerate(header)}
        if rowData['STYLE'] in styles:
            tempstyle = rowData['STYLE']
            temp = rowData['FILENAMES']
            templist = temp.strip("]['").split("', '")
            templist2 = random.sample(templist, n)
            dictstyles[tempstyle] = templist2

# make genre/style folders and create symbolic links in new genre/style specific folders
for genre in genres:
    folderpath = os.path.join(dirname, 'genre_' + genre)
    os.mkdir(folderpath)
    for img in dictgenres[genre]:
        imgpath = os.path.join(sourcedir, img)
        createpath = os.path.join(folderpath, img)
        os.symlink(imgpath, createpath)
for style in styles:
    folderpath = os.path.join(dirname, 'style_' + style)
    os.mkdir(folderpath)
    for img in dictstyles[style]:
        imgpath = os.path.join(sourcedir, img)
        createpath = os.path.join(folderpath, img)
        os.symlink(imgpath, createpath)
