
import os, json, time
import argparse
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim

from dataset import *

#from torch.utils.tensorboard import SummaryWriter

#todo IMPROVEMENT: tensorboard
#writer = SummaryWriter('/home/root/python/UrbanSoundsClassif/runs/lstm')
###################33



# -----------------------------------------------------------
# # RNN/GRU Model
class RNN(nn.Module):
    def __init__(self, input_size, hidden_size, batch_size, num_layers, nb_classes, regularized, dropout, device):
        super(RNN, self).__init__()
        self.batch_size = batch_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.device = device
        self.nb_classes = nb_classes
        self.regularized = regularized
        self.dropout = dropout

        #=====================================================================================
        #for simple RNN remplace GRU by RNN (!!!!!)
        #for LSTM we need to creat e a cell state c_0 (using exactly the same func as for h_0)
        #=====================================================================================

        # input (N    , L  , H_in      )
        # x  -> (batch, seq, input_size)
        self.rnn = nn.GRU(
                input_size = input_size,   #nb of mfcc
                hidden_size = self.hidden_size, #hyper param
                num_layers = self.num_layers,    #hyper param
                dropout = self.dropout,
                batch_first=True,
        )

        self.fc = nn.Linear(
             self.hidden_size,
             self.nb_classes
        )


    def forward(self, x):
        # H_0 (num layers, N, H_out)
        h_0 = torch.zeros(self.num_layers, self.batch_size, self.hidden_size).to(self.device)

        # output ( N , L , H_out)
        out, _ = self.rnn(x, h_0)

        #we only want the final output, at the end of the seq : this ll be the prediction
        # that s to say ( N , H_out)
        #               (batch x hidden_size)
        # the size of our output is the size of the hidden state

        #from the seq column, we keep only the last element
        out = out[ : , -1 , :] #this gives the last line of the output

        out = self.fc(out)

        return out

    def init_hidden(self):
        return torch.zeros(1, self.hidden_size).to(self.device)

    def is_regularized(self):
        return self.regularized

# ------------------------------------------------------------
# # TRAINING
#
def train_single_epoch(model, train_data, optimizer, criterion, L2_LAMBDA, device):
    bench_begin = time.time()
    loss_history = []
    begin_in_bench = time.time()

    for e, (X, y) in enumerate(train_data):
        print(f"-- Episode {e+1} --")
        X, y = X.to(device), y.to(device)

        # input vector has size : torch.Size([N, L, H_in])
        # (batch, seq_len, feat)

        # backprop error
        optimizer.zero_grad()

        pred = model(X.float())
        loss = criterion(pred, y)

        if model.is_regularized():
            #L2 regularization
            l2_norm = 0
            for p in model.parameters() :
                l2_norm += p.pow(2.0).sum()

            loss += L2_LAMBDA * l2_norm

        loss.backward()
        optimizer.step()

        # [ N , classes]
        running_correct = 0

        running_correct += (torch.argmax(pred) == y).sum().item()
        #print(running_correct)
        #print(torch.argmax(pred))
        #exit()



        if e % 10 == 0 and e != 0:
            print(f"-- Episode {e} --> Loss = {loss.item()} -- {round(time.time() - begin_in_bench, 2)}s")
            begin_in_bench = time.time()
            loss_history.append(loss.item())


    print(f"Total Time: {round(time.time() - bench_begin, 2)}s for {e} rounds\n")
    return loss_history

def evaluate_single_epoch(model, data, set, device):
    correct = 0
    c = 0
    with torch.no_grad():
        for X, y in data:
            X, y = X.to(device), y.to(device)
            pred = model(X.float())
            for p in y:
                c += 1
                if y[p].item() == torch.argmax(pred[p]).item():
                    correct += 1
                if c >= set:
                    break
            if c >= set:
                break


    accuracy = correct / c
    print(f"Validation test : Current accuracy: {accuracy} on {c} test samples")
    return accuracy

def train_multi_epoch(model, train_data, test_data, optimizer, criterion, epochs, L2_LAMBDA, batch_size, device):
    loss_history = []
    accuracy_history = []
    timer = time.time()

    for e in range(epochs):
        print(f"---- Beginning epoch {e+1} ----")
        #training
        epoch_loss = train_single_epoch(model, train_data, optimizer, criterion, L2_LAMBDA, device)

        #evaluation (on a single random batch)
        epoch_accuracy = evaluate_single_epoch(model, test_data, 4*32, device)

        # storing
        loss_history.append(epoch_loss)
        accuracy_history.append(epoch_accuracy)

    print(f"Timer : {round(time.time() - timer, 2)}s.\n")
    return loss_history, accuracy_history

# ----------------------------------------------------------------
#
# # TESTING

def test(model, data, device):
    correct = 0
    c = 0
    print(f" --- Testing model on {len(data)} rounds ---")
    for i, (X, y) in enumerate(data):
        with torch.no_grad():
            X, y = X.to(device), y.to(device)
            # X = X.view(-1, X.size()[1] * X.size()[2])
            #print(f"Round {i} ", end='\n')
            pred = model(X.float())
            for p in y:
                c += 1
                if y[p].item() == torch.argmax(pred[p]).item():
                    correct += 1
        # print(f"expect {labels.iloc[y.cpu()]} -- obtained: {labels.iloc[pred.cpu()]}")
    correct /= c
    print(f"Current accuracy: {correct}% on {i} test samples")


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# # MAIN

#==============================================================================================
#===========================  MAIN FUNCTION  ==================================================
#==============================================================================================
if __name__ == "__main__":


    print(f"Welcome to the MLP Urban Sound Classifier -({round(time.time(),2)})")
    print("-------------------------------------\n")

    parser = argparse.ArgumentParser()
    parser.add_argument('--lr',         type=float, required=False, help='Enter the learning rate',         default=5e-4)
    parser.add_argument('--epochs',     type=int,   required=False, help='Enter the number of epochs',      default=1)
    parser.add_argument('--batch',      type=int,   required=False, help='Enter the batch size',            default=32)
    parser.add_argument('--l2',         type=float, required=False, help='Enter the L2 regularisation rate',default=0.)

    parser.add_argument('--sr',         type=float, required=False, help='Enter the target sample rate',    default=22050)
    parser.add_argument('--maxlength',  type=int,   required=False, help='Enter the desired audio length',  default=4)

    parser.add_argument('--hidden',     type=int,   required=False, help='Enter the NN hidden size',        default=128)
    parser.add_argument('--layers',     type=int,   required=False, help='Enter the NN number of layers',   default=2)
    parser.add_argument('--dropout',    type=float,  required=False, help='Enter the dropout value [0;1]',  default=0.)

    parser.add_argument('--disablecuda',type=bool,  required=False, help='Add to disable CUDA references',  default=False)
    parser.add_argument('--USdir',      type=str,   required=False, help='UrbanSound8K directory  /UrbanSound8K/' )
    args = parser.parse_args()

    ##############
    #python main.py --dropout 0.2 --l2 1E-4 --USdir `pwd`/UrbanSound8K/
    ###############


    ### Parameters
    ################## audio parameters
    SAMPLE_RATE = args.sr
    MAX_LENGTH = args.maxlength

    ############### training parameters
    EPOCHS = args.epochs
    BATCH_SIZE = args.batch

    LR = args.lr
    L2_LAMBDA = args.l2 #if args.l2 else 1E-4
    regularized = True if args.l2 else False

    ############### NN parameters
    hidden_size = args.hidden  # H_out (hyper param)
    num_layers = args.layers   # (hyper param)
    dropout = args.dropout

    nb_classes = 10 # output size
    ############3

    # ---------------------------------------------------------------
    # CUDA
    #Using GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if not args.disablecuda else 'cpu'
    print(torch.cuda.get_device_name(0))

    # ---------------------------------------------------------------
    # Loading Data

    #setting directory
    print(os.getcwd())
    # ROOT_DIR = os.getcwd() + '/..'
    # DATA_DIR = ROOT_DIR + '/UrbanSound8K/audio'
    # CSV_FILE = ROOT_DIR + '/UrbanSound8K/metadata/UrbanSound8K.csv'
    ROOT_DIR = args.USdir if args.USdir else os.getcwd() + '/../'
    DATA_DIR = ROOT_DIR + 'audio'
    CSV_FILE = ROOT_DIR + 'metadata/UrbanSound8K.csv'

    print(DATA_DIR, CSV_FILE)

    # open and read csv file
    df = pd.read_csv(CSV_FILE)

    # create the labels list
    labels = pd.DataFrame(df.loc[:, ['classID', 'class']]).set_index('classID')
    labels = labels.drop_duplicates().sort_values('classID')
    print(labels)

    # ---------------------------------------------------------------
    # Prepare Dataset & DataLoader

    # create the data generator
    ds_train = myDataset(SAMPLE_RATE, MAX_LENGTH, DATA_DIR, CSV_FILE, True, device)
    dl_train = create_data_loader(ds_train, BATCH_SIZE)
    ds_test = myDataset(SAMPLE_RATE, MAX_LENGTH, DATA_DIR, CSV_FILE, False, device)
    dl_test = create_data_loader(ds_test, BATCH_SIZE, shuffle = False)

    # ---------------------------------------------------------------
    # Create Model

    # process input size
    seq_size = ds_train[0][0].size()[0] # L
    nb_features = ds_train[0][0].size()[1] # H_in
    input_size = nb_features

    # create the model
    model = RNN(input_size, hidden_size, BATCH_SIZE, num_layers, nb_classes, regularized, dropout, device).to(device)
    print(model)

    #for x,y in dl_train:
        #input = ds_train[0][0].reshape(-1,seq_size,nb_features)
        #break

    ##################
    # todo
    # writer.add_graph(model, x.float())
    # writer.close()
    ##################

    # ---------------------------------------------------------------
    # Training
    optimizer = optim.Adam(model.parameters(), lr=LR)  # , weight_decay=1E-5)
    criterion = nn.CrossEntropyLoss()

    #training

    loss,acc = train_multi_epoch(
        model=model,
        train_data=dl_train,
        test_data= dl_test,
        optimizer=optimizer,
        criterion=criterion,
        epochs=EPOCHS,
        L2_LAMBDA=L2_LAMBDA,
        batch_size=BATCH_SIZE,
        device=device
    )


    # ---------------------------------------------------------------
    # Save Model

    #torch.save(model.state_dict(), f'../RNN_{EPOCHS}.pth')

    # ---------------------------------------------------------------
    # Plot

    #plt.figure()
    plt.plot(loss,acc)
    plt.show()


    #state_dict = torch.load("../MLP_8.pth")
    #model.load_state_dict(state_dict)


    # ---------------------------------------------------------------
    # Evaluate Accuracy on

    #create the data generator

    #test(model, dl_test, device)


"""
================================= BENCH =================================
8 EPOCHS / BATCH 32
------------------

TEST SET :
---------
Current accuracy: 0.6658653846153846% on 25 test samples


VALIDATION :
----------

-- Episode 240 --> Loss = 0.2200358808040619 -- 34.8s
Total Time: 826.72s for 245 rounds

Validation test : Current accuracy: 0.98 on 50 test samples
Timer : 6712.51s.

"""