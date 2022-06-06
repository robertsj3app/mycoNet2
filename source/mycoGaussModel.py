import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import matplotlib.pyplot as plt

whichMold ="my1"
removeDups = True
dataset = np.loadtxt(f"data/{whichMold}yielddata.csv", delimiter=',')
incubation_days = dataset[:,1].tolist()
yield_g = dataset[:,4].tolist()

dups=[idx for idx, item in enumerate(incubation_days) if item in incubation_days[:idx]]
for d in dups:
    incubation_days[d] = -1
    yield_g[d] = -1

if removeDups:
    incubation_days = [value for value in incubation_days if value != -1]
    yield_g = [value for value in yield_g if value != -1]
    
incubation_days, yield_g = zip(*sorted(zip(incubation_days,yield_g),key=lambda x: x[0]))

X = np.asarray(incubation_days).reshape(-1,1)
y = np.asarray(yield_g)

rng = np.random.RandomState(1)
training_indices = rng.choice(np.arange(y.size), size=15, replace=False)
X_train, y_train = X[training_indices], y[training_indices]
kernel = 1 * RBF(length_scale=2, length_scale_bounds=(2.0, 2.5)) + WhiteKernel(noise_level=0.01)
gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10000)
gaussian_process.fit(X_train, y_train)
gaussian_process.kernel_
mean_prediction, std_prediction = gaussian_process.predict(X, return_std=True)

plt.plot(X, y, label=r"Linear connection between points", linestyle="dotted")
plt.scatter(X_train, y_train, label="Observations")
plt.plot(X, mean_prediction, label="Mean prediction")
plt.fill_between(
    X.ravel(),
    mean_prediction - 1.96 * std_prediction,
    mean_prediction + 1.96 * std_prediction,
    alpha=0.5,
    label=r"95% confidence interval",
)
plt.legend()
plt.xlabel("Incubation days")
plt.ylabel("Yield (g/L)")
_ = plt.title("Gaussian process regression on noisy incubation days data with duplicates removed")
plt.show()