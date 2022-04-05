import time
import torch
import torch.nn as nn
import torch.optim as optim

# ------------------------------------------------------------
# # TRAINING
#
def train_single_epoch(model, train_data, optimizer, criterion, L2_LAMBDA): #, device):
    bench_begin = time.time()
    loss_history = []
    begin_in_bench = time.time()

    for e, (X, y) in enumerate(train_data):
        print(f"-- Episode {e+1} --")
        #X, y = X.to(device), y.to(device)

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

        if e >= 20:
            break

    print(f"Total Time: {round(time.time() - bench_begin, 2)}s for {e} rounds\n")
    return loss_history

def evaluate_single_epoch(model, data, set): #, device):
    correct = 0
    c = 0
    with torch.no_grad():
        for X, y in data:
            #X, y = X.to(device), y.to(device)
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

def train_multi_epoch(model, train_data, test_data, optimizer, criterion, epochs, L2_LAMBDA, batch_size): #, device):
    loss_history = []
    accuracy_history = []
    timer = time.time()

    for e in range(epochs):
        print(f"---- Beginning epoch {e+1} ----")
        #training
        epoch_loss = train_single_epoch(model, train_data, optimizer, criterion, L2_LAMBDA) #, device)

        #evaluation (on a single random batch)
        epoch_accuracy = evaluate_single_epoch(model, test_data, 4*32) #, device)

        # storing
        loss_history.append(epoch_loss)
        accuracy_history.append(epoch_accuracy)

    print(f"Timer : {round(time.time() - timer, 2)}s.\n")
    return loss_history, accuracy_history

# ----------------------------------------------------------------
#
# # TESTING

def test(model, data): #, device):
    correct = 0
    c = 0
    print(f" --- Testing model on {len(data)} rounds ---")
    for i, (X, y) in enumerate(data):
        with torch.no_grad():
            #X, y = X.to(device), y.to(device)
            pred = model(X.float())
            for p in y:
                c += 1
                if y[p].item() == torch.argmax(pred[p]).item():
                    correct += 1
        # print(f"expect {labels.iloc[y.cpu()]} -- obtained: {labels.iloc[pred.cpu()]}")
    correct /= c
    print(f"Current accuracy: {correct}% on {i} test samples")