import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF

whichMold ="my1"
dataset = np.loadtxt(f"data/{whichMold}yielddata.csv", delimiter=',')

inc = dataset[:,1]
sed = dataset[:,2]
plat = dataset[:,3]
yld = dataset[:,4]

kernel = 1 * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=9)
gaussian_process.fit(inc, yld)
