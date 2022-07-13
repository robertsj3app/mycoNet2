import numpy as np
from sklearn.exceptions import ConvergenceWarning
import mycologyHelpers as mH
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import warnings

# Compares checksum against stored metadata to determine if the model 
# for whichMold needs to be retrained.
# Will also retrain if trained model file is missing.
def dataChangedSinceLastTrain(config, whichMold):
    checksum = mH.getChecksum(whichMold)
    configChecksum = mH.getConfigChecksum(config, whichMold)
    metadata = mH.readJSON("config", "index")
    if not f"{whichMold}" in list(metadata.keys()) or metadata["environment_checksum"] != f"{mH.getEnvChecksum()}":
        return True
    for k in list(metadata.keys()):
        if (k == f"{whichMold}" and (metadata[k]["data_checksum"] != f"{checksum}" or metadata[k]["config_checksum"] != f"{configChecksum}" or not mH.fileExistsInOutput(f"{metadata[k]['file']}"))):
            return True
    return False

def initConfig():
    defaultConfig = {
        "default": {
            "n_restarts_optimizer" : 1000,
            "n_minimum_data_points" : 10,
            "training_features" : ["incubation_days", "seed_days", "plate_days"],
        },
    }
    if mH.readJSON("config", "config") == {}:
        mH.dumpConfig(defaultConfig)

# Trains GP model for whichMold using given kernel params.
def trainModel(whichMold, config):
    print(f"Beginning train for mold MY{whichMold}... ", end="", flush=True)
    # Only retrain if source data is different.
    if dataChangedSinceLastTrain(config, whichMold):

        # Declare variables and disable sklearn warnings regarding convergence.
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        dataset = []
        myConfig = mH.getConfig(config, whichMold)

        # Pull training features from config, build into query, push results to dataset.
        features = ", ".join(myConfig["training_features"])
        numFeatures = len(myConfig["training_features"])
        query = f"SELECT {features}, yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 and facility != \"Willow Street\" and facility != \"Unknown\" and plug_type != \"Unknown\" ORDER BY `mold_lots`.`mfg_date` ASC;" 
        rawData = mH.SQLQuery(query)
        for d in rawData:
            dataset.append(list(d.values()))

         # Define expected behavior for area of curve outside of spec.
        dataset.append([0] * (numFeatures + 1))
        dataset = np.asarray(dataset)

        # Only train model if there are more than n_minimum_data_points data points, specified in config, otherwise data is insufficient.
        if(len(dataset) > myConfig["n_minimum_data_points"]):
            all_days = np.asarray(dataset[:,0:3])
            yield_g = np.asarray(dataset[:,3])

            # Length scale upper bound limited to prevent bad assumptions due to lack of knowledge of full mold growth curve.
            # This limitation prevents oversmoothing of predicted function due to overestimated covariance.
            # Formula allows bound to grow as the range of days in dataset grows.
            length_scale_bound_upper = 2 * np.average([np.std(all_days[:,0]), np.std(all_days[:,1]), np.std(all_days[:,2])])
            length_scale = [1.0] * numFeatures
            n_restarts_optimizer = myConfig["n_restarts_optimizer"]

            # Build kernel and fit model on dataset
            kernel = 1 * RBF(length_scale=length_scale, length_scale_bounds=(1, length_scale_bound_upper)) + WhiteKernel()
            gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts_optimizer)
            gaussian_process.fit(all_days, yield_g)
            
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
    initConfig()
    config = mH.readJSON("config", "config")
    query = "SELECT mold_id from molds WHERE 1"
    mold_ids = []
    rawData = mH.SQLQuery(query)
    for d in rawData:
        mold_ids.append(d["mold_id"])

    mH.toggleLog(True)
    print(f"Beginning training on {mH.getDateTime()}")
    for i in mold_ids:
        trainModel(i, config)
    mH.toggleLog(False)

trainAllModels()