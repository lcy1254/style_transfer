import sys
import os
import csv

infopath = '/Users/chaeyounglee/Desktop/style transfer research/train_info.csv'
genreoutpath = '/Users/chaeyounglee/Desktop/style transfer research/genre-count.csv'
styleoutpath = '/Users/chaeyounglee/Desktop/style transfer research/style-count.csv'

genres = set()
styles = set()
count = {'genre': {}, 'style':{}}

with open(infopath, 'r') as csvFile:
    csvReader = csv.reader(csvFile)
    header = next(csvReader)
    for row in csvReader:
        rowData = {key: row[idx] for idx, key in enumerate(header)}
        try:
            genre = rowData['genre']
            if genre in genres:
                count['genre'][genre] = count['genre'][genre] + 1
            else:
                genres.add(genre)
                count['genre'][genre] = 1
        except (ValueError, AttributeError):
            print('Failed to read genre from %s' %(row))
        try:
            style = rowData['style']
            if style in styles:
                count['style'][style] = count['style'][style] + 1
            else:
                styles.add(style)
                count['style'][style] = 1
        except (ValueError, AttributeError):
            print('Failed to read style from %s' %(row))

dict1 = count['genre']
dict2 = count['style']
with open(genreoutpath, 'w') as file:
    writer = csv.writer(file)
    writer.writerow(['', 'GENRE', 'COUNT'])
    for key, value in dict1.items():
        writer.writerow(['genre', key, value])
        
with open(styleoutpath, 'w') as file:
    writer = csv.writer(file)
    writer.writerow(['', 'STYLE', 'COUNT'])
    for key, value in dict2.items():
        writer.writerow(['style', key, value])
