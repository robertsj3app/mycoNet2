import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, Matern
import matplotlib.pyplot as plt
import pickle

whichMold ="my17"
removeDups = False
dataset = np.loadtxt(f"data/{whichMold}yielddata.csv", delimiter=',')
#all_days = dataset[:,3].tolist()
all_days = dataset[:,1:4]
yield_g = dataset[:,4].tolist()

if removeDups:
    dups=[idx for idx, item in enumerate(all_days) if item in all_days[:idx]]
    for d in dups:
        all_days[d] = -1
        yield_g[d] = -1
    all_days = [value for value in all_days if value != -1]
    yield_g = [value for value in yield_g if value != -1]
    
#all_days, yield_g = zip(*sorted(zip(all_days,yield_g),key=lambda x: x[0]))

X = np.asarray(all_days)#.reshape(-1,1)
y = np.asarray(yield_g)

size = len(y)

rng = np.random.RandomState(1)
training_indices = rng.choice(np.arange(y.size), size=size, replace=False)
X_train, y_train = X[training_indices], y[training_indices]
kernel = 1 * RBF(length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(1.0, 2.3)) + WhiteKernel()
#kernel = 1 * Matern(length_scale=1.0, length_scale_bounds=(1.0, 2.4), nu = 2.0) + WhiteKernel()
#kernel = 1 * RBF(length_scale=1.0, length_scale_bounds=(1.0, 2.0)) + WhiteKernel()
gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=20000)
gaussian_process.fit(X_train, y_train)
gaussian_process.kernel_
mean_prediction, std_prediction = gaussian_process.predict(X, return_std=True)

with open(f"output/{whichMold}_gauss.dump" , "wb") as f:
     pickle.dump(gaussian_process, f) 

#all_days, yield_g, mean_prediction = zip(*sorted(zip(dataset[:,0].tolist(),yield_g,mean_prediction),key=lambda x: x[0]))

plt.plot(all_days, yield_g, label=r"Linear connection between points", linestyle="dotted")
plt.scatter(all_days, yield_g, label="Observations")
plt.plot(all_days, mean_prediction, label="Mean prediction")
plt.fill_between(
    X.ravel(),
    mean_prediction - std_prediction,
    mean_prediction + std_prediction,
    alpha=0.5,
    label=r"95% confidence interval",
)
plt.legend()
plt.xlabel("Incubation days")
plt.ylabel("Yield (g/L)")
_ = plt.title("Gaussian process regression on noisy incubation days data with duplicates included")
plt.show()