# -*- coding: utf-8 -*-
"""NLPProject_Sent2Vec_ArticleBias

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19H1DFJLFF087RgLv2mvY1j9_RKbX_fUJ
"""

from google.colab import drive
drive.mount('/content/drive')

from torch.utils.data import Dataset
import pandas as pd
import os
import numpy as np
import torch

import gensim
from gensim.test.utils import common_texts
from gensim.models.doc2vec import Doc2Vec, TaggedDocument

from os import path as osp
from tqdm import tqdm
import random
import json

root_folder = "/content/drive/MyDrive/NLP/data"
embedding_size = 384
split_type = "random" # media
dataset = "article_bias" # new_b

!pip install -U sentence-transformers

from torch.utils.data import Dataset
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

df = pd.read_table(osp.join(root_folder, "splits", split_type, f"train.tsv"))

from pandas.io import parsers
from torch.utils.data import Dataset

class VectorDataset(Dataset):
    def __init__(self, filename, doc2vecmodel, save=False):
      df = pd.read_table(osp.join(root_folder, "splits", split_type, f"{filename}.tsv"))
      self.vectors = []
      count = 0
      for file_name in df["ID"]:
          with open(osp.join(root_folder, "jsons", file_name + ".json")) as json_file:
            d = json.load(json_file)
            content = d['content']
            vector = model.encode(content)
            self.vectors.append(vector)
          count += 1
          if count > 10000:
            break
      self.vectors = np.array(self.vectors)
      np.save(osp.join(root_folder, f"{dataset}sent2vec_" + str(embedding_size) + filename), self.vectors, allow_pickle=True, fix_imports=True)

class SentimentDataset(Dataset):
    def __init__(self, filename, save=False):
        df = pd.read_table(osp.join(root_folder, "splits", split_type, f"{filename}.tsv"))
        self.labels = []
        count = 0
        for label in df["bias"]:
          self.labels.append(label)
          count += 1
          if count > 10000:
            break
        self.vectors = np.load(osp.join(root_folder, f"{dataset}sent2vec__" + str(embedding_size) + filename + ".npy"))

    def __len__(self):
        assert len(self.labels) == len(self.vectors)
        return len(self.vectors)

    def __getitem__(self, idx):
        label = self.labels[idx] # for 11 classes
        # 0 liberal, 1 neutral, 2 conservative
        # label = 0 if row[0] < 5 else 1
        sample = { "label": label, "data": self.vectors[idx] }
        return sample

# save numpy vectors for train and test sentences
train_object = VectorDataset("train", model)
test_object = VectorDataset("test", model)

train_data = SentimentDataset("train")
test_data = SentimentDataset("test")

from torch.utils.data import DataLoader

# load train and test data samples into dataloader
batch_size = 32
train_loader = DataLoader(dataset=train_data, batch_size=batch_size, shuffle=True) 
test_loader = DataLoader(dataset=test_data, batch_size=batch_size, shuffle=False)

# build custom module for logistic regression
class MLP(torch.nn.Module):    
    def __init__(self, n_inputs, n_outputs, hidden_size=256):
        super(MLP, self).__init__()
        self.linear1 = torch.nn.Linear(n_inputs, hidden_size)
        self.linear2 = torch.nn.Linear(hidden_size, hidden_size)
        self.linear3 = torch.nn.Linear(hidden_size, hidden_size)
        self.linear4 = torch.nn.Linear(hidden_size, n_outputs)

    def forward(self, x):
        x = torch.relu(self.linear1(x))
        x = torch.relu(self.linear2(x))
        x = torch.relu(self.linear3(x))
        y_pred = self.linear4(x)
        return y_pred

n_inputs = embedding_size
n_outputs = 3
hidden_size = 256
classifier = MLP(n_inputs, n_outputs, hidden_size)

# defining the optimizer
optimizer = torch.optim.Adam(classifier.parameters(), lr=0.001)
# defining Cross-Entropy loss
criterion = torch.nn.CrossEntropyLoss()

epochs = 50
Loss = []
acc = []
for epoch in range(epochs):
    classifier.train()
    for i, batch in enumerate(train_loader):
        optimizer.zero_grad()
        outputs = classifier(batch['data'].float())
        loss = criterion(outputs, batch['label'])
        # Loss.append(loss.item())
        loss.backward()
        optimizer.step()
    Loss.append(loss.item())
    train_correct = 0
    test_correct = 0

    classifier.eval()
    for train_batch in train_loader:
        outputs = classifier(train_batch['data'].float())
        _, predicted = torch.max(outputs.data, 1)
        train_correct += (predicted == train_batch['label']).sum()

    for test_batch in test_loader:
        outputs = classifier(test_batch['data'].float())
        _, predicted = torch.max(outputs.data, 1)
        test_correct += (predicted == test_batch['label']).sum()

    train_accuracy = 100 * (train_correct.item()) / len(train_data)
    test_accuracy = 100 * (test_correct.item()) / len(test_data)
    acc.append(test_accuracy)
    print('Epoch: {}. Loss: {}. Training Accuracy: {}'.format(epoch, loss.item(), train_accuracy))
    print('Epoch: {}. Testing Accuracy: {}'.format(epoch, test_accuracy))

