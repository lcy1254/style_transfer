# -*- coding: utf-8 -*-
"""wilds_stainAug_res50_toshare_chaeyoung.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1WZuQpbKpesTN-dbtAnomzpa7kL028d-_
"""

!which jupyter

!nvidia-smi

import os
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID" 
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Commented out IPython magic to ensure Python compatibility.
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
# %matplotlib inline

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data
import torch.utils.data as data
import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils
import torchvision.models as models
import torch.nn.init as init

batchSize=32
imgSize=int(96)
num_classes = 2

from histomicstk.preprocessing.augmentation.color_augmentation import rgb_perturb_stain_concentration

class stain_augment(object):
    def __call__(self, sample):
        sample = np.array(sample)
        rgbaug = rgb_perturb_stain_concentration(sample, sigma1=1., sigma2=1.)
        return rgbaug

# plt.imshow(rgb_perturb_stain_concentration(imgs[0], sigma1=1., sigma2=1.))

augment = transforms.Compose([stain_augment(),
                              transforms.ToPILImage(),
                              # transforms.Resize(imgSize),
                              transforms.RandomResizedCrop(imgSize),
                              transforms.RandomHorizontalFlip(p=0.5),
                              transforms.RandomVerticalFlip(p=0.5),
                              # transforms.RandomResizedCrop(imgSize, scale=(0.8, 1.0), ratio=(1, 1)),
                              transforms.ToTensor(),
                              transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

transform = transforms.Compose([transforms.ToPILImage(),
                                transforms.Resize(imgSize),
                                transforms.ToTensor(),
                                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

data_root_path = '../data/patches'
csv_path = '../data/metadata_fnames_splits_modSplit.csv'
# error_path = "../data/error_stainNorm.txt"

df = pd.read_csv(csv_path); df.shape

# fnames = df.fnames.tolist(); len(fnames)

# error = []
# for i in range(len(fnames)):
#     sample_ = Image.open(fnames[i])
#     sample_ = np.array(sample_)
    
#     if sample_.shape[2] == 4:
#         sample_ = sample_[:,:,:3]
#     elif sample_.shape[2] != 3:
#         raise ValueError('image channel num is not 3')
    
#     try:
#         rgbaug = rgb_perturb_stain_concentration(sample_, sigma1=1., sigma2=1.)
#     except Exception as e:
#         error.append(i)
#         print(f'error_{i}_{e}')

# error, len(error)

# import json
# with open("../data/error_stainAug.txt", "w") as fp:
#     json.dump(error, fp)
# with open("../data/error_stainAug.txt", "r") as fp:
#     error2 = json.load(fp)

# error == error2

# len(error2)

data_root_path = '../data/patches'
csv_path = '../data/metadata_fnames_splits_modSplit.csv'
error_path = "../data/error_stainAug.txt"

class MyDataset(data.Dataset):
    def __init__(self, data_root_path=data_root_path, csv_path=csv_path, error_path=error_path, dset_type='train', transform=None):
        """
        dset_type: ["train", "val", "test"]
        """

        df = pd.read_csv(csv_path)
        with open(error_path, "r") as fp:
            error = json.load(fp)
        df = df.drop(df.index[error])
        
        self.df = df[df.data_split==dset_type]
        self.fnames = self.df.fnames.tolist()
        self.labels = self.df.tumor.tolist()
        self.transform=transform

    def __getitem__(self, index):
        fname = self.fnames[index]
        label = self.labels[index]
        img = np.array(Image.open(fname), dtype='uint8')
        
        if img.shape[2] == 4:
            img = img[:,:,:3]
        elif img.shape[2] != 3:
            raise ValueError('image channel num is not 3')
        
        if self.transform is not None:
            img = self.transform(img)
        return img, label

    def __len__(self):
        return len(self.df)

datasets = {}
loaders = {}

for dset_type in ['train', 'val', 'test']:
    if dset_type == 'train':
        datasets[dset_type] = MyDataset(dset_type=dset_type, transform = augment)
        loaders[dset_type] = torch.utils.data.DataLoader(datasets[dset_type], batch_size=batchSize, shuffle=True, num_workers=4, pin_memory=True)
    elif dset_type == 'val':
        datasets[dset_type] = MyDataset(dset_type=dset_type, transform = transform)
        loaders[dset_type] = torch.utils.data.DataLoader(datasets[dset_type], batch_size=batchSize, shuffle=True, num_workers=4, pin_memory=True)
    elif dset_type == 'test':
        datasets[dset_type] = MyDataset(dset_type=dset_type, transform = transform)
        loaders[dset_type] = torch.utils.data.DataLoader(datasets[dset_type], batch_size=batchSize, shuffle=False, num_workers=4, pin_memory=True)
    print('Finished loading %s dataset: %s samples' % (dset_type, len(datasets[dset_type])))

def get_model(num_classes):

#     model = models.mobilenet_v2(pretrained=True)
#     model.classifier = nn.Sequential(nn.Dropout(p=0.2), nn.Linear(1280, num_classes))
    
    model = models.resnet50(pretrained=True)
    num_ftrs = model.fc.in_features
    model.classifier = nn.Sequential(nn.Dropout(p=0.2), nn.Linear(num_ftrs, num_classes))
    
    return model

def train_model(model, loaders, criterion, optimizer, scheduler, num_epochs=40, estop=5):
    since = time.time()

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    best_loss = float("inf")
    counter = 0

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)
        
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0.0

            for inputs, labels in loaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()
                
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

                ##########
                
#             while True:
#                 try:
#                     inputs, labels = next(loaders[phase])

#                     inputs = inputs.to(device)
#                     labels = labels.to(device)

#                     optimizer.zero_grad()

#                     with torch.set_grad_enabled(phase == 'train'):
#                         outputs = model(inputs)
#                         _, preds = torch.max(outputs, 1)
#                         loss = criterion(outputs, labels)

#                         if phase == 'train':
#                             loss.backward()
#                             optimizer.step()

#                     running_loss += loss.item() * inputs.size(0)
#                     running_corrects += torch.sum(preds == labels.data)
                
#                 except:
#                     pass

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

            if phase == 'val':
                if scheduler is not None:
                    scheduler.step(epoch_loss)
                    
                if epoch_loss < best_loss:
                    best_epoch = epoch
                    best_loss = epoch_loss
                    best_acc = epoch_acc
                    best_model_wts = copy.deepcopy(model.state_dict())
                    counter = 0
                else:
                    counter += 1

        print()

        if counter >= estop:
            break

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))
    print('Best val Loss: {:4f}'.format(best_loss))

    model.load_state_dict(best_model_wts)

    return model, best_loss, best_acc, best_epoch

import warnings
warnings.simplefilter(action='ignore', category=RuntimeWarning)

model = get_model(num_classes)
model = model.to('cuda')

params_to_update = []
for name, param in model.named_parameters():
    if param.requires_grad == True:
        params_to_update.append(param)

optimizer = optim.SGD(params_to_update, lr=0.004, momentum=0.9, nesterov=True)
criterion = nn.CrossEntropyLoss()

dataset_sizes = {x: len(datasets[x]) for x in ['train', 'val', 'test']}
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

model, best_loss, best_acc, best_epoch = \
    train_model(model, loaders, criterion, optimizer, scheduler=None, num_epochs=40, estop=5)
torch.save(model.state_dict(), 'state_dicts/wilds_stain_augmentation_res50_modSplit3.pth')

warnings.filterwarnings('default')

def test_model(model, loader, dataset_size, criterion):
    
    print('-' * 10)
    model.eval()
    running_loss = 0.0
    running_corrects = 0
    whole_probs = torch.FloatTensor(dataset_size)
    whole_labels = torch.LongTensor(dataset_size)
    
    with torch.no_grad():

        # Iterate over data.
        for i, data in enumerate(loader):
            inputs = data[0].to(device)
            labels = data[1].to(device)

            # forward
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)

            # statistics
            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

            outputs = F.softmax(outputs, dim=1)
            whole_probs[i*batchSize:i*batchSize+inputs.size(0)]=outputs.detach()[:,1].clone()
            whole_labels[i*batchSize:i*batchSize+inputs.size(0)]=labels.detach().clone()

        total_loss = running_loss / dataset_size
        total_acc = running_corrects.double() / dataset_size

    print('Test Loss: {:.4f} Acc: {:.4f}'.format(total_loss, total_acc))

    return whole_probs.cpu().numpy(), whole_labels.cpu().numpy(), total_loss, total_acc

from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
import itertools
from sklearn.metrics import roc_curve, auc, roc_auc_score

from sklearn.metrics import roc_auc_score
def bootstrap_auc(y_true, y_pred, n_bootstraps=1000, rng_seed=42):
    n_bootstraps = n_bootstraps
    rng_seed = rng_seed  # control reproducibility
    bootstrapped_scores = []

    rng = np.random.RandomState(rng_seed)
    for i in range(n_bootstraps):
        # bootstrap by sampling with replacement on the prediction indices
        indices = rng.randint(len(y_pred), size=len(y_pred))
        if len(np.unique(y_true[indices])) < 2:
            # We need at least one positive and one negative sample for ROC AUC
            # to be defined: reject the sample
            continue
        score = roc_auc_score(y_true[indices], y_pred[indices])
        bootstrapped_scores.append(score)
#         print("Bootstrap #{} ROC area: {:0.3f}".format(i + 1, score))
    bootstrapped_scores = np.array(bootstrapped_scores)

    print("Confidence interval for the score: [{:0.3f} - {:0.3}]".format(
        np.percentile(bootstrapped_scores, (2.5, 97.5))[0], np.percentile(bootstrapped_scores, (2.5, 97.5))[1]))
    
    return np.percentile(bootstrapped_scores, (2.5, 97.5))[0], np.percentile(bootstrapped_scores, (2.5, 97.5))[1]

def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix')

    print(cm)

    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 1.5
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

prob_test, label_test, loss_test, acc_test = test_model(model, loaders['test'], dataset_sizes['test'], criterion)

pred_test = [1 if prob>0.50 else 0 for prob in prob_test]

cm = confusion_matrix(label_test, pred_test)
print(cm)
acc = (cm[0][0]+cm[1][1])/len(pred_test)*100
print('accuracy = ' + str(acc))

print(f'tile-wise AUC is {roc_auc_score(label_test, prob_test)}')

false_positive_rate, true_positive_rate, thresholds = roc_curve(label_test, prob_test)
roc_auc = auc(false_positive_rate, true_positive_rate)
ci_low, ci_high = bootstrap_auc(np.array(label_test), np.array(prob_test))
print(f'AUROC = {roc_auc} with 95CI of {ci_low}-{ci_high}')

plot_confusion_matrix(cm, classes=["normal", "tumor"])

plt.title("Receiver Operating Characteristic")
plt.plot(false_positive_rate, true_positive_rate, color="teal", label="AUC = %0.2f" % roc_auc)
plt.legend(loc="lower right")
plt.plot([0,1],[0,1], color="lightcoral", ls="--")
plt.xlim([-0.1, 1.2])
plt.ylim([-0.1, 1.2])
plt.ylabel("True Positive Rate")
plt.xlabel("False Positive Rate")
plt.show()











# to get all probs

# model2 = models.mobilenet_v2(pretrained=True)
# model2.classifier = nn.Sequential(nn.Dropout(p=0.2), nn.Linear(1280, num_classes))
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# model2.cuda()
# model_path = 'msi_pytorch2_stainAug_trainOnNatmed_unfreezeAll_sgdlr4e-3_epoch30_estop5_2.pth'
# state_dict = torch.load(model_path)
# model2.load_state_dict(state_dict)

# augment = transforms.Compose([# transforms.ToPILImage(),
#                               # transforms.Resize(imgSize),
#                               transforms.RandomResizedCrop(imgSize),
#                               transforms.RandomHorizontalFlip(p=0.5),
#                               transforms.RandomVerticalFlip(p=0.5),
#                               # transforms.RandomResizedCrop(imgSize, scale=(0.8, 1.0), ratio=(1, 1)),
#                               transforms.ToTensor(),
#                               transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

# transform = transforms.Compose([# transforms.ToPILImage(),
#                                 transforms.Resize(imgSize),
#                                 transforms.ToTensor(),
#                                 transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

# class ImageFolderWithPaths(dset.ImageFolder):
#     """Custom dataset that includes image file paths. Extends
#     torchvision.datasets.ImageFolder
#     """
#     # override the __getitem__ method. this is the method that dataloader calls
#     def __getitem__(self, index):
#         # this is what ImageFolder normally returns 
#         original_tuple = super(ImageFolderWithPaths, self).__getitem__(index)
#         # the image file path
#         path = self.imgs[index][0]
#         # make a new tuple that includes original and the path
#         tuple_with_path = (original_tuple + (path,))
#         return tuple_with_path

# def train_data_():
#     data_path = '../data/naturemed/mssmsi/TRAIN'
#     train_dataset = ImageFolderWithPaths(
#         root=data_path,
#         transform=augment,
#     )
#     train_loader = torch.utils.data.DataLoader(
#         train_dataset,
#         batch_size=64,
# #         num_workers=0,
#         shuffle=True,
#     )
#     return train_dataset, train_loader

# def test_data():
#     data_path = '../data/naturemed/mssmsi/TEST'
#     test_dataset = ImageFolderWithPaths(
#         root=data_path,
#         transform=transform,
#     )
#     test_loader = torch.utils.data.DataLoader(
#         test_dataset,
#         batch_size=2,
# #         num_workers=0,
#         shuffle=False,
#     )
#     return test_dataset, test_loader

# test_dataset, test_loader = test_data()

# test_dataset_size = len(test_dataset)

# criterion = nn.CrossEntropyLoss()
# sm = nn.Softmax(dim = 1)
# def test(model, dataloader, dataset_size):
#     running_corrects = 0
#     running_loss=0
#     pred = []
#     true = []
#     pred_wrong = []
#     true_wrong = []
#     image = []
#     paths = []
#     prob = []

#     for batch_idx, (data, target, path) in enumerate(dataloader):
#         data, target = data.to(device), target.to(device)
#         data = data.type(torch.cuda.FloatTensor)
#         target = target.type(torch.cuda.LongTensor)
#         model.eval()
#         output = model(data)
#         loss = criterion(output, target)
#         output = sm(output)
#         _, preds = torch.max(output, 1)
#         running_corrects += torch.sum(preds == target.data)
#         running_loss += loss.item() * data.size(0)
#         preds = preds.cpu().numpy()
#         target = target.cpu().numpy()
#         probs = output.detach().cpu().numpy()[:,1]
#         preds = np.reshape(preds,(len(preds),1))
#         target = np.reshape(target,(len(preds),1))
#         data = data.cpu().numpy()

#         for i in range(len(preds)):
#             pred.append(preds[i])
#             true.append(target[i])
#             prob.append(probs[i])
#             paths.append(path[i])
#             if(preds[i]!=target[i]):
#                 pred_wrong.append(preds[i])
#                 true_wrong.append(target[i])
#                 image.append(data[i])

#     epoch_acc = running_corrects.double()/dataset_size
#     epoch_loss = running_loss/dataset_size
#     print(epoch_acc,epoch_loss)
#     return true,pred,prob,paths,image,true_wrong,pred_wrong

# true_,pred_,prob_,paths_,image_,true_wrong_,pred_wrong_ = test(model2, test_loader, test_dataset_size)

# slides_ = ['-'.join(os.path.basename(i).split('-')[2:5]) for i in paths_]

# unique = list(set(slides_))

# df = pd.DataFrame(columns=['id', 'prob', 'pred', 'label'])

# df.id = slides_
# df.prob = prob_
# df.pred = [i[0] for i in pred_]
# df.label = [i[0] for i in true_]

# pt_prob=[]
# pt_pred=[]
# pt_label=[]
# for i in range(len(unique)):
#     ave_prob=np.mean(df[df.id==unique[i]].prob.values)
#     s=1 if ave_prob>0.76 else 0
#     y=df[df.id==unique[i]].label.values.tolist()[0]
#     pt_prob.append(ave_prob)
#     pt_pred.append(s)
#     pt_label.append(y)

# df = pd.DataFrame(columns=['id', 'prob', 'pred', 'label'])
# df.id = unique
# df.prob = pt_prob
# df.pred = pt_pred
# df.label = pt_label

# df.to_csv('../data/stainAug_trainOnNatmed_testOnNatmed_probs.csv', index=False)

# df
