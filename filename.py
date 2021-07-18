import os
import sys
import random
import csv

csvpath = '/Users/chaeyounglee/Desktop/style transfer research/train_info.csv'

genres = {}
styles = {}

with open(csvpath, 'r') as csvFile:
    csvReader = csv.reader(csvFile)
    header = next(csvReader)
    for row in csvReader:
        rowData = {key: row[idx] for idx, key in enumerate(header)}
        style = rowData['style']
        genre = rowData['genre']
        filename = rowData['filename']
        try:
            genres[genre].append(filename)
        except:
            genres[genre] = [filename]
        try:
            styles[style].append(filename)
        except:
            styles[style] = [filename]

with open(os.path.join(os.path.dirname(csvpath), 'genre_filename.csv'), 'w') as file:
    writer = csv.writer(file)
    writer.writerow(['GENRE', 'FILENAMES'])
    for key, value in genres.items():
        writer.writerow([key, value])

with open(os.path.join(os.path.dirname(csvpath), 'style_filename.csv'), 'w') as file:
    writer = csv.writer(file)
    writer.writerow(['STYLE', 'FILENAMES'])
    for key, value in styles.items():
        writer.writerow([key, value])
