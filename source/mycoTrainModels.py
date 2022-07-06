import numpy as np
import os
import mycologyHelpers as mH
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

def dataChangedSinceLastTrain(whichMold):
    checksum = mH.getChecksum(whichMold)
    metadata = mH.readMetaData()
    if not f"{whichMold}" in list(metadata.keys()):
        return True
    for k in list(metadata.keys()):
        if (k == f"{whichMold}" and (metadata[k]["checksum"] != f"{checksum}" or not os.path.exists(f"output/{metadata[k]['file']}"))):
            return True
    return False

def trainModel(whichMold, length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(1.0, 2.6), n_restarts_optimizer=2000):
    if dataChangedSinceLastTrain(whichMold):
        dataset = []
        query = f"SELECT incubation_days, seed_days, plate_days, yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 and facility = \"Lenoir\" ORDER BY `mold_lots`.`mfg_date` ASC;" 
        rawData = mH.SQLQuery(query)
        for d in rawData:
            dataset.append([d["incubation_days"], d["seed_days"], d["plate_days"], d["yield_per_liter"]])
    
        dataset = np.asarray(dataset)
        all_days = np.asarray(dataset[:,0:3])
        yield_g = np.asarray(dataset[:,3])

        print(all_days)
        print(yield_g)

        kernel = 1 * RBF(length_scale=length_scale, length_scale_bounds=length_scale_bounds) + WhiteKernel()
        gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts_optimizer)
        gaussian_process.fit(all_days, yield_g)
        gaussian_process.kernel_

        mH.dumpTrainedModel(f"my{whichMold}_gauss.dump", gaussian_process, whichMold, mH.getChecksum(whichMold))
    else:
        print(f"Aborting train for mold MY{whichMold}, source data has not changed since last train.")

trainModel(1)


