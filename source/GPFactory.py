# GPFactory.py
# Defines a Singleton Factory pattern class for generating trained GaussianProcessRegressor models on MySQL data.
# Includes functions for training models and interfacing with MySQL database.
# Note that functions which interface with database assume inputs to be properly formatted.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com

from DBConnection import DBConnection
from json import dump
from mycologyHelpers import envChecksum, dictChecksum, initConfig, readJSON
from numpy import asarray, average, std
from os import path
import pickle
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.exceptions import ConvergenceWarning
from typing_extensions import Self
from warnings import filterwarnings

class GPFactory(object):

    # Define class variables.
    __outputDir: str = path.join(path.dirname(__file__), "../output") 
    __configDir: str = path.join(path.dirname(__file__), "../config")
    __config: dict = None
    __index: dict = None
    __db_connection: DBConnection = None

    # Factory is a singleton pattern object.
    def __new__(cls: object):
        if not hasattr(cls, 'instance'):
            cls.instance = super(GPFactory, cls).__new__(cls)
        return cls.instance
    
    # When instantiated, create a connection to the database and figure out directory locations.
    def __init__(self: Self):
        initConfig()
        self.__config = readJSON(self.__configDir, "config")
        self.__index = readJSON(self.__configDir, "index")
        self.__db_connection = DBConnection(self.__config["credentials"]["username"], self.__config["credentials"]["password"])

    # Builds training config from config file, falling through to defaults where needed.
    def __extractConfig(self: Self, whichMold: int):
        myConfig = self.__config["default"].copy()
        if f"{whichMold}" in self.__config.keys():
            for f in self.__config[f"{whichMold}"].keys():
                myConfig[f] = self.__config[f"{whichMold}"][f]
        return myConfig

    # Generates output dump file, index file entry, and database queries from trained model.
    def __generateOutput(self: Self, model: GaussianProcessRegressor, whichMold: int):
        self.__dumpTrainedModel(model, whichMold)
        self.__updateMetaData(whichMold)
        self.__pushModelResults(model, whichMold)

    def __getSpec(self:Self, whichMold: int):
        spec = None
        query = f"SELECT incubation_days_min, incubation_days_max, seed_days_min, seed_days_max, plate_days_min, plate_days_max FROM specs where spec_id = (SELECT spec_id from molds where mold_id = {whichMold});"
        rawData = self.__db_connection.SQLQuery(query)
        for d in rawData:
            spec = d
        return spec
        
    # Generates appropriate queries for a trained model and pushes its results to the gp_predictions table in the SQL database
    def __pushModelResults(self: Self, model: GaussianProcessRegressor, whichMold: int):
        
        spec = self.__getSpec(whichMold)

        inc = list(range(spec["incubation_days_min"], spec["incubation_days_max"]))
        sed = list(range(spec["seed_days_min"], spec["seed_days_max"]))
        plt = list(range(spec["plate_days_min"], spec["plate_days_max"]))
        query = f"DELETE FROM gp_predictions WHERE mold_id = {whichMold}"
        self.__db_connection.SQLQuery(query)
        print(f"Uploading results to database... ", end="", flush=True)

        for i in inc:
            for s in sed:
                for p in plt:
                    thisparams = [i,s,p]                
                    predicted_yield, predicted_stdev = model.predict([thisparams], return_std=True)
                    lotweeks = self.calculateLotWeeks(whichMold, i, predicted_yield[0])
                    query = f"INSERT INTO gp_predictions (mold_id, incubation_days, seed_days, plate_days, predicted_average_yield_per_liter, std_deviation, `lot*weeks`) VALUES ({whichMold}, {i}, {s}, {p}, {predicted_yield[0]}, {predicted_stdev[0]}, {lotweeks})"
                    try:
                        self.__db_connection.SQLQuery(query)
                    except Exception as e:
                        print(e)

        print(f"Success.")
    
    # Updates index file entry for mold number whichMold.
    def __updateMetaData(self: Self, whichMold: int):
        self.__index["environment_checksum"] = f"{envChecksum()}"
        self.__index[f"{whichMold}"] = {
            "file" : f"my{whichMold}_gauss.dump",
            "data_checksum" : f"{self.__getDataChecksum(whichMold)}",
            "config_checksum" : f"{dictChecksum(self.__extractConfig(whichMold))}"
        }
        with open(f"{self.__configDir}/index.json",'w+') as indexFile:
            dump(self.__index, indexFile, indent = 4)

    # Pickles a trained model and dumps it to outputDir, then updates
    # the corresponding mold's metadata accordingly
    def __dumpTrainedModel(self: Self, model: GaussianProcessRegressor, whichMold: int):
        with open(f"{self.__outputDir}/my{whichMold}_gauss.dump" , "wb") as f:
            pickle.dump(model, f) 
    
    # Returns CRC32 checksum of data corresponding to mold number whichMold.
    # Used to check if data has been updated to prevent needless retraining.
    def __getDataChecksum(self: Self, whichMold: int):
        query = f"SELECT SUM(CRC32(lot_id)) from mold_lots WHERE mold_id = {whichMold};"
        rawData = self.__db_connection.SQLQuery(query)
        checksum = -1
        for d in rawData:
            checksum = d["SUM(CRC32(lot_id))"]
        return checksum  

    # Calculates lot*weeks performance metric for a given mold entry.
    # Used to determine optimal growth by factoring in time constraints and annual demand.
    # Must be calculated through code since MySQL does not allow for generated columns using data from several tables.
    # Formula:
    # X = yield/vessel
    # Y = growth days
    # K = Annual Demand / (# Vessels * 7) = Arbitrary constant
    # Lot*Weeks = Y*K/X
    def calculateLotWeeks(self: Self, whichMold: int, incubationDays: int, predictedYield: int):
        query = f"SELECT vessel_size_l from incubation_methods where method = (SELECT incubation_method from specs where spec_id = (SELECT spec_id from molds where mold_id = {whichMold}));"
        rawData = self.__db_connection.SQLQuery(query)[0]
        vesselSize = rawData["vessel_size_l"]
        yieldPerVessel = predictedYield * vesselSize
        query = f"SELECT annual_demand, num_vessels from molds where mold_id = {whichMold}"
        rawData = self.__db_connection.SQLQuery(query)[0]
        annualDemand = rawData["annual_demand"]
        numVessels = rawData["num_vessels"]
        lotweeks = (incubationDays * (annualDemand / (numVessels * 7))) / yieldPerVessel
        if lotweeks <= 0 or lotweeks > 200:
            lotweeks = 200
        return lotweeks
        
    # Compares checksums against stored metadata to determine if the model 
    # for whichMold needs to be retrained.
    def dataChangedSinceLastTrain(self: Self, whichMold: int):
        checksum = self.__getDataChecksum(whichMold)
        configChecksum = dictChecksum(self.__extractConfig(whichMold))

        # Will retrain if any of the following conditions are met:
        # 1) Mold has no entry stored in index.json
        # 2) Environment checksum has changed.
        # 3) Source data checksum has changed.
        # 4) Configuration checksum has changed.
        # 5) Mold has an entry in index.json but the corresponding .dump file is missing.
        if not f"{whichMold}" in list(self.__index.keys()) or self.__index["environment_checksum"] != f"{envChecksum()}":
            return True
        for k in list(self.__index.keys()):
            if (k == f"{whichMold}" and (self.__index[k]["data_checksum"] != f"{checksum}" or self.__index[k]["config_checksum"] != f"{configChecksum}" or not path.exists(f"{self.__outputDir}/{self.__index[k]['file']}"))):
                return True
        return False

    # Trains GP model for whichMold using given kernel params.
    def trainModel(self: Self, whichMold: int):
        print(f"Beginning train for mold MY{whichMold}... ", end="", flush=True)

        # Only retrain if source data is different.
        if self.dataChangedSinceLastTrain(whichMold):

            # Declare variables and disable sklearn warnings regarding convergence.
            filterwarnings("ignore", category=ConvergenceWarning)
            dataset = []
            myConfig = self.__extractConfig(whichMold)

            # Pull training features from config, build into query, push results to dataset.
            numFeatures = 3
            conditionals = " AND ".join(myConfig["conditionals"])
            numConditionals = len(myConfig["conditionals"])
            query = f"SELECT incubation_days, seed_days, plate_days, yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 {'AND ' + conditionals if numConditionals > 0 else ''} ORDER BY `mold_lots`.`mfg_date` ASC;" 
            rawData = self.__db_connection.SQLQuery(query)
            for d in rawData:
                dataset.append(list(d.values()))

            # Define expected behavior for area of curve outside of spec and convert to array.
            spec = self.__getSpec(whichMold)
            dataset[:] = [x for x in dataset if not x[0] > spec["incubation_days_max"] or x[1] > spec["seed_days_max"] or x[2] > spec["plate_days_max"]]
            dataset.append([0] * (numFeatures + 1))
            dataset = asarray(dataset)

            # Only train model if there are more than n_minimum_data_points data points, specified in config, otherwise data is insufficient.
            if(len(dataset) > myConfig["n_minimum_data_points"]):
                training_features = asarray(dataset[:,0:numFeatures])
                yield_g = asarray(dataset[:,numFeatures])

                # Length scale upper bound limited to prevent bad assumptions due to lack of knowledge of full mold growth curve.
                # This limitation prevents oversmoothing of predicted function due to overestimated covariance.
                # Formula allows bound to grow as the range of data in dataset grows.
                #length_scale_bound_upper = 2 * average([std(training_features[:,0]), std(training_features[:,1]), std(training_features[:,2])])
                inc = list(range(spec["incubation_days_min"], spec["incubation_days_max"]))
                sed = list(range(spec["seed_days_min"], spec["seed_days_max"]))
                plt = list(range(spec["plate_days_min"], spec["plate_days_max"]))
                length_scale_bound_upper = average([std(inc), std(sed), std(plt)])
                length_scale = [1.0] * numFeatures
                n_restarts_optimizer = myConfig["n_restarts_optimizer"]

                # Build kernel and fit model on dataset
                kernel = 1 * RBF(length_scale=length_scale, length_scale_bounds=(1, length_scale_bound_upper)) + WhiteKernel()
                gaussian_process = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts_optimizer)
                gaussian_process.fit(training_features, yield_g)
            
                # Dump trained model and update metadata
                print("Success.")
                print(f"Resulting kernel params: {gaussian_process.kernel_}")
                self.__generateOutput(gaussian_process, whichMold)
            else:
                print(f"Aborting, insufficient source data.")
        else:
            print(f"Aborting, source data has not changed since last train.")
