from importlib.metadata import metadata
import os
import heapq
from numpy import sort
import requests
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
print("Initializing...")
from tensorflow.keras.models import load_model
import pickle
import mycologyHelpers as mH

# print("Pulling latest trained models...")

# if not os.path.exists("./models"):
#     os.makedirs("./models")

# index_file = requests.get("https://raw.githubusercontent.com/robertsj3app/mycoNet2/main/output/index.txt", allow_redirects=True)
# lines = index_file.text.strip().split('\n')

# for l in lines:
#     file = requests.get(f"https://github.com/robertsj3app/mycoNet2/raw/main/output/{l}", allow_redirects=True)
#     open(f"models/{l}", 'wb').write(file.content)
#     print(f"Found {l}...")

os.system('cls' if os.name == 'nt' else 'clear')

def intInput(prompt):
    inp = -1
    try:
        inp = int(input(prompt))
    except ValueError:
        inp = -1
    return inp

def select_model():
    files = []
    for file in os.listdir("./output"):
        if file.endswith(".h5") or file.endswith(".dump"):
            files.append(file)

    print("Select a model to query:")
    i = 0
    files = sort(files)
    for f in files:
        i += 1
        print(f"{i}: {f}")

    inp = intInput("> ")
    if inp <= i and inp > 0:
        file = files[inp-1]
        if file.endswith(".h5"):
            modelType = "neural"
        else:
            modelType = "gauss"

        if modelType == "neural":
            model = load_model(f"./output/{file}")
        else:
            model = pickle.load(open(f"./output/{file}", "rb"))
        print(f"Loading model {file}...\n")
        metadata = mH.readMetaData()
        for k in list(metadata.keys()):
            if metadata[k]["file"] == file:
                whichMold = k
                select_query_mode(model, modelType, whichMold)
        print("Fatal error: tried to load model with missing metadata!")
        select_model()
    else:
        print("Bad selection\n")
        select_model()

def select_query_mode(model, modelType, whichMold):
    print("Select query mode:\n1: Manual query\n2: Request best prediction\n3: Back")
    inp = intInput("> ")
    if inp == 1:
        manual_query(model, modelType, whichMold)
    elif inp == 2:
        get_num_queries(model, modelType, whichMold)
    elif inp == 3:
        select_model()
    else:
        print("Bad selection\n")
        select_query_mode(model, modelType)

def get_num_queries(model, modelType, whichMold):
    num = intInput("Enter desired number of top predictions: ")
    request_prediction(model, num, modelType, whichMold)

def manual_query(model, modelType, whichMold):
    inc = sed = plt = -1
    inc_min = inc_max = seed_min = seed_max = plate_min = plate_max = 0
    query = f"SELECT incubation_days_min, incubation_days_max, seed_days_min, seed_days_max, plate_days_min, plate_days_max FROM specs WHERE spec_id = (SELECT spec_id FROM molds WHERE mold_id = {whichMold});"
    rawData = mH.SQLQuery(query)
    for d in rawData:
        inc_min = d["incubation_days_min"]
        inc_max = d["incubation_days_max"]
        seed_min = d["seed_days_min"]
        seed_max = d["seed_days_max"]
        plate_min = d["plate_days_min"]
        plate_max = d["plate_days_max"]       

    while(inc < inc_min or inc > inc_max):
        inc = intInput(f"Enter number of incubation days ({inc_min} - {inc_max}): ")
    while(sed < 6 or sed > 21):
        sed = intInput(f"Enter number of seed days ({seed_min} - {seed_max}): ")
    while(plt < 3 or plt > 17):
        plt = intInput(f"Enter number of plate days ({plate_min} - {plate_max}): ")
    qur = [inc, sed, plt]

    if modelType == "neural":
        result = model.predict([qur])
        print(f"Model predicts that {qur} will give a yield of {result}.\n")
    else:
        result, stdev = model.predict([qur], return_std=True)
        print(f"Model predicts that {qur} will give a yield of {result} with a standard deviation of +/- {stdev}.\n")
    select_query_mode(model, modelType)

def request_prediction(model, num, modelType):
    inc_min = inc_max = seed_min = seed_max = plate_min = plate_max = 0
    query = f"SELECT incubation_days_min, incubation_days_max, seed_days_min, seed_days_max, plate_days_min, plate_days_max FROM specs WHERE spec_id = (SELECT spec_id FROM molds WHERE mold_id = {whichMold});"
    rawData = mH.SQLQuery(query)
    for d in rawData:
        inc_min = d["incubation_days_min"]
        inc_max = d["incubation_days_max"]
        seed_min = d["seed_days_min"]
        seed_max = d["seed_days_max"]
        plate_min = d["plate_days_min"]
        plate_max = d["plate_days_max"] 
    inc = list(range(inc_min,inc_max)) # spec calls for as low as 7 days
    sed = list(range(seed_min,seed_max))
    plt = list(range(plate_min, plate_max)) #spec can go up to 21
    preds = []
    stdevs = []
    # best_pred = -1
    params = []
    for i in inc:
        for s in sed:
            for p in plt:
                thisparams = [i,s,p]
                print(f"Trying {thisparams}...", end='\r', flush=True)
                manual_prediction = ''
                if modelType == "neural":
                    manual_prediction = model.predict([thisparams])
                else:
                    manual_prediction, manual_stdev = model.predict([thisparams], return_std=True)
                    stdevs.append(manual_stdev)
                preds.append(manual_prediction)
                params.append(thisparams)
                # if(manual_prediction[0] > best_pred):
                #     best_pred = manual_prediction[0]
                #     params = thisparams

    n_largest_indices = heapq.nlargest(num, range(len(preds)), preds.__getitem__)
    print(f"\nTop {num} predictions:")
    if modelType == "neural":
        print("Inc\tSeed\tPlate\tYield")
    else:
        print("Inc\tSeed\tPlate\tMean Yield\tStd. Dev\tRange")
    for n in n_largest_indices:
        
        if modelType == "neural":
            print(f"{round(params[n][0],3)}\t{round(params[n][1],3)}\t{round(params[n][2],3)}\t{str(round(preds[n][0][0],3))}")
        else:
            print(f"{round(params[n][0],3)}\t{round(params[n][1],3)}\t{round(params[n][2],3)}\t{round(preds[n][0],3)}\t\t{round(stdevs[n][0],3)}\t\t{round(preds[n][0] - stdevs[n][0], 3)} - {round(preds[n][0] + stdevs[n][0],3)}")
    # print(f"Network claims that {params} is best with a yield of {best_pred}\n")
    select_query_mode(model, modelType)
    
    
select_model()