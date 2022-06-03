import numpy
import sys
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.utils import normalize
from keras import backend as K
from tensorflow.keras.layers import Dense, Input, Dropout
from tensorflow.keras.optimizers import Adam, SGD
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.models import load_model
import os

test = True
whichMold ="my5"

dataset = numpy.loadtxt(f"data/{whichMold}yielddata2010-current.csv", delimiter=',')
X = dataset[:,1:4]
y = dataset[:,4]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33)

model = Sequential()
model.add(Input(3))
model.add(Dense(256, activation='relu'))
model.add(Dropout(0.25))
model.add(Dense(512, activation='relu'))
model.add(Dense(512, activation='relu'))
model.add(Dropout(0.35))
model.add(Dense(256, activation='relu'))
model.add(Dense(256, activation='relu'))
model.add(Dense(1, activation='linear'))

model.compile(loss='mean_squared_error',
              metrics=['mean_absolute_percentage_error'],
              optimizer=Adam(learning_rate=0.001))


mc = ModelCheckpoint(f"output/{whichMold}_best_model_revised_data.h5", monitor='val_loss', mode='min', save_best_only=True)
es = EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=1000)

history = model.fit(X_train, y_train, batch_size=64,
          epochs=10000,
          validation_data=(X_test, y_test),
          verbose=1,
          callbacks=[es, mc])

best_model = load_model(f"output/{whichMold}_best_model_revised_data.h5")
train_acc = best_model.evaluate(X_train, y_train, verbose=0)
test_acc = best_model.evaluate(X_test, y_test, verbose=0)
prediction = best_model.predict(X)
#manual_prediction = best_model.predict([[29,12,10]])


print(f"\nBest Model:\nTrain: {train_acc}, Test: {test_acc}\n")
print("Predictions:\n")
print("Inc\tSeed\tPlate\tPredicted Yield/L*Days\tError")

j = 0
for i in prediction:
    print(f"{X[j][0]}\t{X[j][1]}\t{X[j][2]}\t{i}\t{i[0] - y[j]}\n")
    j+=1


# print(f"manual pred\n{manual_prediction}")


orig_stdout = sys.stdout
with open(f"output/{whichMold}_predictions.txt", 'w') as f:
    sys.stdout = f
    print(f"\nBest Model:\nTrain: {train_acc}, Test: {test_acc}\n")
    print("Predictions:\n")
    print("Inc\tSeed\tPlate\tPredicted Yield/L*Days\tError")

    j = 0
    for i in prediction:
        print(f"{X[j][0]}\t{X[j][1]}\t{X[j][2]}\t{i}\t{i[0] - y[j]}\n")
        j+=1
sys.stdout = orig_stdout

inc = list(range(12,31)) # spec calls for as low as 7 days
seed = list(range(6,22))
plate = list(range(3,18)) #spec can go up to 21

if(test == True):
    best_pred = -1
    best_params = []
    runnerup_pred = -1
    runnerup_params = []
    for i in inc:
        for s in seed:
            for p in plate:
                params = [i,s,p]
                print(f"Trying {params}...\n")
                manual_prediction = best_model.predict([params])
                if(manual_prediction[0] > best_pred):
                    runnerup_pred = best_pred
                    runnerup_params = best_params
                    best_pred = manual_prediction[0]
                    best_params = params
    print(f"Network claims that {best_params} is best with a yield of {best_pred}\n")
    print(f"Network claims that {runnerup_params} is second best with a yield of {runnerup_pred}\n")

files = []
for file in os.listdir("./output"):
    if file.endswith(".h5"):
        files.append(file)
orig_stdout = sys.stdout
with open(f"output/index.txt", 'w') as f:
    sys.stdout = f
    for f in files:
        print(f)
sys.stdout = orig_stdout
