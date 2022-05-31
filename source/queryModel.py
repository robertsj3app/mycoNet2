import os
import heapq
import requests
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
print("Initializing...")
from tensorflow.keras.models import load_model
print("Pulling latest trained models...")


user = 'my_github_username'
psw = ''

def select_model():
    files = []
    for file in os.listdir("./models"):
        if file.endswith(".h5"):
            files.append(file)

    print("Select a model to query:")
    i = 0
    for f in files:
        i += 1
        print(f"{i}: {f}")

    inp = int(input("> "))
    model = 0
    if inp <= i and inp > 0:
        file = files[inp-1]
        model = load_model(f"./models/{file}")
        print(f"Loading model {file}...\n")
        select_query_mode(model)
    else:
        print("Bad selection")
        select_model()

def select_query_mode(model):
    print("Select query mode:\n1: Manual query\n2: Request best prediction\n3: Back")
    inp = int(input("> "))
    if inp == 1:
        manual_query(model)
    elif inp == 2:
        get_num_queries(model)
    elif inp == 3:
        select_model()
    else:
        print("Bad selection\n")
        select_query_mode(model)

def get_num_queries(model):
    num = int(input("Enter desired number of top predictions: "))
    request_prediction(model, num)

def manual_query(model):
    inc = int(input("Enter number of incubation days: "))
    sed = int(input("Enter number of seed days: "))
    plt = int(input("Enter number of plate days: "))
    qur = [inc, sed, plt]
    result = model.predict([qur])
    print(f"Model predicts that {qur} will give a yield of {result}.")
    select_query_mode(model)

def request_prediction(model, num):
    inc = list(range(12,31)) # spec calls for as low as 7 days
    sed = list(range(6,22))
    plt = list(range(3,18)) #spec can go up to 21
    preds = []
    # best_pred = -1
    params = []
    for i in inc:
        for s in sed:
            for p in plt:
                thisparams = [i,s,p]
                print(f"Trying {thisparams}...", end='\r', flush=True)
                manual_prediction = model.predict([thisparams], verbose=False)
                preds.append(manual_prediction)
                params.append(thisparams)
                # if(manual_prediction[0] > best_pred):
                #     best_pred = manual_prediction[0]
                #     params = thisparams

    n_largest_indices = heapq.nlargest(num, range(len(preds)), preds.__getitem__)
    print(f"\nTop {num} predictions:")
    print("Inc\tSeed\tPlate\tYield")
    for n in n_largest_indices:
        print(f"{params[n][0]}\t{params[n][1]}\t{params[n][2]}\t{preds[n][0]}")
    # print(f"Network claims that {params} is best with a yield of {best_pred}\n")
    select_query_mode(model)
    
    
select_model()