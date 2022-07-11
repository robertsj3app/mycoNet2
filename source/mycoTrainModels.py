import numpy as np
from sklearn.exceptions import ConvergenceWarning
import mycologyHelpers as mH
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import warnings


N_MINIMUM_DATA_POINTS = 10

# Compares checksum against stored metadata to determine if the model 
# for whichMold needs to be retrained.
# Will also retrain if trained model file is missing.
def dataChangedSinceLastTrain(whichMold):
    checksum = mH.getChecksum(whichMold)
    metadata = mH.readMetaData()
    if not f"{whichMold}" in list(metadata.keys()):
        return True
    for k in list(metadata.keys()):
        if (k == f"{whichMold}" and (metadata[k]["checksum"] != f"{checksum}" or not mH.fileExistsInOutput(f"{metadata[k]['file']}"))):
            return True
    return False

# Trains GP model for whichMold using given kernel params.
def trainModel(whichMold, length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(1.0, 2.6), n_restarts_optimizer=2000):
    print(f"Beginning train for mold MY{whichMold}... ", end="", flush=True)

    # Only retrain if source data is different.
    if dataChangedSinceLastTrain(whichMold):
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        dataset = []
        query = f"SELECT incubation_days, seed_days, plate_days, yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 and facility = \"Lenoir\" ORDER BY `mold_lots`.`mfg_date` ASC;" 
        rawData = mH.SQLQuery(query)
        for d in rawData:
            dataset.append([d["incubation_days"], d["seed_days"], d["plate_days"], d["yield_per_liter"]])
    
        dataset = np.asarray(dataset)

        # Only train model if there are more than 10 data points, otherwise data is insufficient.
        # 10 is probably still too few ? 
        if(len(dataset) > N_MINIMUM_DATA_POINTS):
            all_days = np.asarray(dataset[:,0:3])
            yield_g = np.asarray(dataset[:,3])

            kernel = 1 * RBF(length_scale=length_scale, length_scale_bounds=length_scale_bounds) + WhiteKernel()
            gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts_optimizer)
            gaussian_process.fit(all_days, yield_g)
            gaussian_process.kernel_

            # Dump trained model and update metadata
            mH.dumpTrainedModel(f"my{whichMold}_gauss.dump", gaussian_process, whichMold, mH.getChecksum(whichMold))
            print("Success.")
        else:
            print(f"Aborting, insufficient source data.")
    else:
        print(f"Aborting, source data has not changed since last train.")

# Pull a list of all mold ids from server, call trainModel for each mold id.
def trainAllModels(length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(1.0, 2.6), n_restarts_optimizer=2000):
    query = "SELECT mold_id from molds WHERE 1"
    mold_ids = []
    rawData = mH.SQLQuery(query)
    for d in rawData:
        mold_ids.append(d["mold_id"])

    mH.toggleLog(True)
    print(f"Beginning training on {mH.getDateTime()}")
    for i in mold_ids:
        trainModel(i, length_scale=length_scale, length_scale_bounds=length_scale_bounds, n_restarts_optimizer=n_restarts_optimizer)
    mH.toggleLog(False)

trainAllModels(n_restarts_optimizer=2000)