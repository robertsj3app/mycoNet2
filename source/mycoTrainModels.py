# mycoTrainModels.py
# A group of functions used to define training behavior for gaussian process models and enact training.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com

import numpy as np
from sklearn.exceptions import ConvergenceWarning
import mycologyHelpers as mH
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from warnings import filterwarnings

# Compares checksums against stored metadata to determine if the model 
# for whichMold needs to be retrained.
# Will also retrain if trained model file is missing.
def dataChangedSinceLastTrain(config, whichMold):
    checksum = mH.getChecksum(whichMold)
    configChecksum = mH.getConfigChecksum(config, whichMold)
    metadata = mH.readJSON("config", "index")

    # Will retrain if any of the following conditions are met:
    # 1) Mold has no entry stored in index.json
    # 2) Environment checksum has changed.
    # 3) Source data checksum has changed.
    # 4) Configuration checksum has changed.
    # 5) Mold has an entry in index.json but the corresponding .dump file is missing.
    if not f"{whichMold}" in list(metadata.keys()) or metadata["environment_checksum"] != f"{mH.getEnvChecksum()}":
        return True
    for k in list(metadata.keys()):
        if (k == f"{whichMold}" and (metadata[k]["data_checksum"] != f"{checksum}" or metadata[k]["config_checksum"] != f"{configChecksum}" or not mH.fileExistsInOutput(f"{metadata[k]['file']}"))):
            return True
    return False

# Trains GP model for whichMold using given kernel params.
def trainModel(whichMold, config):
    print(f"Beginning train for mold MY{whichMold}... ", end="", flush=True)
    # Only retrain if source data is different.
    if dataChangedSinceLastTrain(config, whichMold):

        # Declare variables and disable sklearn warnings regarding convergence.
        filterwarnings("ignore", category=ConvergenceWarning)
        dataset = []
        myConfig = mH.getConfig(config, whichMold)

        # Pull training features from config, build into query, push results to dataset.
        features = ", ".join(myConfig["additional_training_features"]) + ", "
        numFeatures = len(myConfig["additional_training_features"]) + 3
        conditionals = " AND ".join(myConfig["conditionals"])
        numConditionals = len(myConfig["conditionals"])
        query = f"SELECT incubation_days, seed_days, plate_days, {features if numFeatures > 3 else ''}yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 {'AND ' + conditionals if numConditionals > 0 else ''} ORDER BY `mold_lots`.`mfg_date` ASC;" 
        print(query)
        rawData = mH.SQLQuery(query)
        for d in rawData:
            dataset.append(list(d.values()))

         # Define expected behavior for area of curve outside of spec.
        dataset.append([0] * (numFeatures + 1))
        dataset = np.asarray(dataset)

        # Only train model if there are more than n_minimum_data_points data points, specified in config, otherwise data is insufficient.
        if(len(dataset) > myConfig["n_minimum_data_points"]):
            training_features = np.asarray(dataset[:,0:numFeatures])
            yield_g = np.asarray(dataset[:,numFeatures])

            # Length scale upper bound limited to prevent bad assumptions due to lack of knowledge of full mold growth curve.
            # This limitation prevents oversmoothing of predicted function due to overestimated covariance.
            # Formula allows bound to grow as the range of days in dataset grows.
            length_scale_bound_upper = 2 * np.average([np.std(training_features[:,0]), np.std(training_features[:,1]), np.std(training_features[:,2])])
            length_scale = [1.0] * numFeatures
            n_restarts_optimizer = myConfig["n_restarts_optimizer"]

            # Build kernel and fit model on dataset
            kernel = 1 * RBF(length_scale=length_scale, length_scale_bounds=(1, length_scale_bound_upper)) + WhiteKernel()
            gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts_optimizer)
            gaussian_process.fit(training_features, yield_g)
            
            # Dump trained model and update metadata
            print("Success.")
            print(f"Resulting kernel params: {gaussian_process.kernel_}")
            mH.dumpTrainedModel(f"my{whichMold}_gauss.dump", gaussian_process, whichMold, mH.getChecksum(whichMold), mH.getConfigChecksum(config, whichMold))
        else:
            print(f"Aborting, insufficient source data.")
    else:
        print(f"Aborting, source data has not changed since last train.")

# Pull a list of all mold ids from server, call trainModel for each mold id.
def trainAllModels():
    mH.toggleLog()
    mH.initConfig()

    config = mH.readJSON("config", "config")
    query = "SELECT mold_id from molds WHERE 1"
    mold_ids = []
    rawData = mH.SQLQuery(query)
    for d in rawData:
        mold_ids.append(d["mold_id"])
    
    print(f"Beginning training on {mH.getDateTime()}")
    for i in mold_ids:
        trainModel(i, config)
    mH.toggleLog()

trainAllModels()