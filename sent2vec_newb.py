# -*- coding: utf-8 -*-
"""NLPProject_Sent2Vec_NewB.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1llea5QSEvgN5BiVRVCsggilBY8LTjurJ
"""

from google.colab import drive
drive.mount('/content/drive')

from torch.utils.data import Dataset
import pandas as pd
import os
import random
import numpy as np
import torch
torch_device = torch.device("cpu")
from tqdm import tqdm

import gensim
from gensim.test.utils import common_texts
from gensim.models.doc2vec import Doc2Vec, TaggedDocument

from os import path as osp
from tqdm import tqdm

# root_folder = "/content/drive/MyDrive/NLP/NewB-master/"
root_folder = "/content/drive/MyDrive/NLP/NewB-master/"
embedding_size = 384
dataset = "newb"

!pip install -U sentence-transformers

from torch.utils.data import Dataset
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

from torch.utils.data import Dataset

class VectorDataset(Dataset):
    def __init__(self, filename, doc2vecmodel, save=False):
        self.data = pd.read_table(osp.join(root_folder, filename), header=None)
        size = len(self.data)
        self.vectors = np.zeros((size, embedding_size))
        for idx in tqdm(range(size)):
            vector = model.encode(self.data.iloc[idx][1])
            self.vectors[idx] = vector
        np.save(osp.join(root_folder, f"{dataset}sent2vec_" + str(embedding_size) + filename), self.vectors, allow_pickle=True, fix_imports=True)

class SentimentDataset(Dataset):
    def __init__(self, filename, save=False):
        self.data = pd.read_table(osp.join(root_folder, filename), header=None)
        self.vectors = np.load(osp.join(root_folder, f"{dataset}sent2vec_" + str(embedding_size) + filename + ".npy"))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        # label = row[0] # for 11 classes
        # 0 liberal, 1 neutral, 2 conservative
        label = 0 if row[0] < 5 else 2 if row[0] > 5 else 1
        sample = { "label": label, "data": self.vectors[idx] }
        return sample

# save numpy vectors for train and test sentences
train_object = VectorDataset("train_orig.txt", model)
test_object = VectorDataset("test.txt", model)

train_data = SentimentDataset("train_orig.txt")
test_data = SentimentDataset("test.txt")

from torch.utils.data import DataLoader
# load train and test data samples into dataloader
batch_size = 32
train_loader = DataLoader(dataset=train_data, batch_size=batch_size, shuffle=True) 
test_loader = DataLoader(dataset=test_data, batch_size=batch_size, shuffle=False)

# build custom module for logistic regression
class MLP(torch.nn.Module):    
    def __init__(self, n_inputs, n_outputs, hidden_size=256):
        super(MLP, self).__init__()
        self.dropout = torch.nn.Dropout(p=0.2)
        self.linear1 = torch.nn.Linear(n_inputs, hidden_size)
        self.linear2 = torch.nn.Linear(hidden_size, hidden_size)
        self.linear3 = torch.nn.Linear(hidden_size, hidden_size)
        self.linear4 = torch.nn.Linear(hidden_size, n_outputs)

    def forward(self, x):
        x = torch.relu(self.linear1(self.dropout(x)))
        x = torch.relu(self.linear2(self.dropout(x)))
        x = torch.relu(self.linear3(x))
        y_pred = self.linear4(x)
        return y_pred

n_inputs = embedding_size
n_outputs = 3
hidden_size = 256
classifier = MLP(n_inputs, n_outputs, hidden_size)

# defining the optimizer
optimizer = torch.optim.Adam(classifier.parameters(), lr=1e-4)
# defining Cross-Entropy loss
criterion = torch.nn.CrossEntropyLoss()

epochs = 30
Loss = []
acc = []

for epoch in range(epochs):
    classifier.train()
    train_correct = 0
    for i, batch in enumerate(train_loader):
        optimizer.zero_grad()
        outputs = classifier(batch['data'].float())
        # _, pred = outputs.data.topk(5, 1, True, True)
        # correct = pred.eq(batch['label'].view(-1, 1).expand_as(pred))
        # train_correct += correct.reshape(-1).float().sum(0)
        loss = criterion(outputs, batch['label'])
        # Loss.append(loss.item())
        loss.backward()
        optimizer.step()
    Loss.append(loss.item())

    classifier.eval()
    test_correct = 0
    for test_batch in test_loader:
        outputs = classifier(test_batch['data'].float())
        _, predicted = torch.max(outputs.data, 1)
        test_correct += (predicted == test_batch['label']).sum()
        # _, pred = outputs.data.topk(5, 1, True, True)
        # correct = pred.eq(test_batch['label'].view(-1, 1).expand_as(pred))
        # test_correct += correct.reshape(-1).float().sum(0)

    # train_accuracy = 100 * (train_correct.item()) / len(train_data)
    test_accuracy = 100 * (test_correct.item()) / len(test_data)
    acc.append(test_accuracy)
    # print('Epoch: {}. Loss: {}. Training Accuracy: {}'.format(epoch, loss.item(), train_accuracy))
    print('Epoch: {}. Testing Accuracy: {}'.format(epoch, test_accuracy))

from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

n_labels = ["Newsday (L)", "New York Times (L)", "Cable News Network (L)", "Los Angeles Times (L)", "Washington Post (L)", "Politico (N)", "Wall Street Journal (C)", "New York Post (C)", "Daily Press (C)", "Daily Herald (C)", "Chicago Tribune (C)"]

y_true = []
y_pred = []

test_correct = 0
for test_batch in test_loader:
    outputs = classifier(test_batch['data'].float())
    # _, predicted = torch.max(outputs.data, 1)
    # test_correct += (predicted == test_batch['label']).sum()
    _, pred = outputs.data.topk(5, 1, True, True)
    correct = pred.eq(test_batch['label'].view(-1, 1).expand_as(pred))
    test_correct += correct.reshape(-1).float().sum(0)

    y_true.extend(test_batch['label'].tolist())
    y_pred.extend(pred[:, 0].tolist())

y_true = np.array(y_true)
y_pred = np.array(y_pred)

cm = confusion_matrix(y_true, y_pred, normalize="pred")
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=n_labels)
disp.plot(xticks_rotation="vertical", include_values=False, cmap="YlGnBu")
plt.show()

import seaborn as sns
import matplotlib.pyplot as plt

sns.heatmap(cm, annot=False, fmt='f', cmap='YlGnBu')
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.title('Confusion Matrix Heatmap')
plt.show()

# l=0
# for c in cm1:
#     plt.scatter([str(n) for n in range(10)],c,label="Top "+str(l))
#     l=l+1
# plt.xlabel('X Values')
# plt.ylabel('Y Values')
# plt.legend()
# plt.show()

for n in range(1, 6):
  test_correct = 0
  for test_batch in test_loader:
      outputs = classifier(test_batch['data'].float())
      _, pred = outputs.data.topk(n, 1, True, True)
      correct = pred.eq(test_batch['label'].view(-1, 1).expand_as(pred))
      test_correct += correct.reshape(-1).float().sum(0)
  test_accuracy = 100 * (test_correct.item()) / len(test_data)
  print(f"Top-{n} Accuracy: {test_accuracy}")

sentence = "trump was seen yesterday on television in mcdonalds commercials"
embedding = model.encode(sentence)

classifier(torch.as_tensor(embedding)).argmax()

tensor([0.5327, 0.0747, 0.3926], grad_fn=<SoftmaxBackward0>) "he called trump a puppet a novice and an extremist"
tensor([0.4803, 0.0760, 0.4437], grad_fn=<SoftmaxBackward0>) "he called trump a puppet and a novice"
tensor([0.5167, 0.0461, 0.4372], grad_fn=<SoftmaxBackward0>) "he called trump a puppet"
tensor([0.4611, 0.0390, 0.5000], grad_fn=<SoftmaxBackward0>) "he called trump a genius"

sentence = "he called trump a puppet"
embedding = model.encode(sentence)

sm = torch.nn.Softmax(dim=0)
sm(classifier(torch.as_tensor(embedding)))

avoid = [
    'trump', 'legendary', 'best', 'great', 'acclaimed', 'iconic', 'visionary', 'outstanding',
    'leading', 'celebrated', 'popular', 'award-winning', 'landmark', 'cutting-edge',
    'innovative', 'revolutionary', 'extraordinary', 'brilliant', 'hit', 'famous',
    'renowned', 'remarkable', 'prestigious', 'world-class', 'respected', 'notable',
    'virtuoso', 'honorable', 'awesome', 'unique', 'pioneering', 'phenomenal', 'cult',
    'racist', 'perverted', 'sexist', 'homophobic', 'transphobic', 'misogynistic',
    'sect', 'fundamentalist', 'heretic', 'extremist', 'denialist', 'terrorist',
    'freedom fighter', 'bigot', 'myth', 'neo-Nazi', '-gate', 'pseudo-', 'controversial',
    'supposed', 'apparent', 'purported', 'alleged', 'accused', 'so-called', 'notably',
    'it should be noted', 'arguably', 'interestingly', 'essentially', 'utterly',
    'actually', 'clearly', 'absolutely', 'of course', 'without a doubt', 'indeed',
    'happily', 'sadly', 'tragically', 'aptly', 'fortunately', 'unfortunately',
    'untimely', 'but', 'despite', 'however', 'though', 'although', 'furthermore',
    'while', 'reveal', 'point out', 'clarify', 'expose', 'explain', 'find', 'note',
    'observe', 'insist', 'speculate', 'surmise', 'claim', 'assert', 'admit', 'confess',
    'deny', 'passed away', 'gave her life', 'eternal rest', 'make love', 'an issue with',
    'collateral damage', 'recently', 'lately', 'currently', 'today', 'presently',
    'to date', '15 years ago', 'formerly', 'in the past', 'traditionally',
    'this/last/next (year/month/winter/spring/summer/fall/autumn)', 'yesterday',
    'tomorrow', 'in the future', 'now', 'soon', 'since'
]

res = [ele for ele in avoid if(ele in sentence)]

print(res)

from nltk.corpus import wordnet
  
synonyms = []
for syn in wordnet.synsets("terrorist"):
    for l in syn.lemmas():
        synonyms.append(l.name())

synonyms

import nltk
nltk.download('wordnet')

