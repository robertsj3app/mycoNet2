import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import pickle
from mysql import connector
from mysql.connector import errorcode

whichMold ="1"
dataset = []

try:
    connection = connector.connect(user="python", password="gaussianProcess", host="localhost", database="mycology")
except connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
else:
    cursor = connection.cursor()
    query = f"SELECT incubation_days, seed_days, plate_days, yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 and facility = \"Lenoir\" ORDER BY `mold_lots`.`mfg_date` ASC;"
    cursor.execute(query)

    for (incubation_days, seed_days, plate_days, yield_per_liter) in cursor:
        dataset.append([incubation_days, seed_days, plate_days, yield_per_liter])

    cursor.close()
    connection.close()

#dataset = np.loadtxt(f"data/{whichMold}yielddata.csv", delimiter=',')
dataset = np.array(dataset)
all_days = dataset[:,0:3]
yield_g = dataset[:,3].tolist()

X = np.asarray(all_days)#.reshape(-1,1)
y = np.asarray(yield_g)

print(all_days)
print (yield_g)

kernel = 1 * RBF(length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(1.0, 2.3)) + WhiteKernel()
gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=2000)
gaussian_process.fit(X, y)
gaussian_process.kernel_
mean_prediction, std_prediction = gaussian_process.predict(X, return_std=True)

with open(f"output/{whichMold}_gauss.dump" , "wb") as f:
     pickle.dump(gaussian_process, f) 