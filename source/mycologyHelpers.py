# myclogyHelpers.py
# A group of functions used to facilitiate interfacing with the mycology SQL database.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com
from string import hexdigits
from mysql import connector
from mysql.connector import errorcode
from json import load, dump, dumps
from json.decoder import JSONDecodeError
import pickle
from os import path, makedirs
import sys
from datetime import date, datetime
from zlib import crc32

# Define directory all outputs (index file and trained models) go to. Defined relative to location of script. 
outputDir = path.join(path.dirname(__file__), "../output") 
configDir = path.join(path.dirname(__file__), "../config")
# Define logger class that dumps stdout to logfile based on date of instantiation as well as terminal.
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        if not path.exists(f"{outputDir}/logs/"):
            makedirs(f"{outputDir}/logs")
        self.log = open(f"{outputDir}/logs/training_log_{date.today()}.txt", "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message) 

    def flush(self):
        self.terminal.flush()
        self.log.flush()
        pass

def crc32Opt(fileName):
    with open(fileName, 'rb') as fh:
        hash = 0
        while True:
            s = fh.read(65536)
            if not s:
                break
            hash = crc32(s, hash)
        return "%08X" % (hash & 0xFFFFFFFF)

# Toggle whether logging is active. Date of instantiating the logger is used until logging toggled off and on again.
def toggleLog(bool):
    if bool == True:
        sys.stdout = Logger()
    else:
        sys.stdout = sys.__stdout__

# Return string showing current date and time
def getDateTime():
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    date = now.date()
    return f"{date} at {time}"

# Return true if filename exists in outputDir (defined at top)
def fileExistsInOutput(filename):
    return path.exists(f"{outputDir}/{filename}")

# Read outputDir/index.json into a dictionary
def readJSON(whichDir, filename):
    dict = {}
    if whichDir == "config":
        dir = configDir
    elif whichDir == "output":
        dir = outputDir
    else:
        print ("Bad directory choice")
        exit(1)
    try:
        with open(f"{dir}/{filename}.json",'r') as file:
            try:
                dict = load(file)
            except JSONDecodeError:
                if(filename == "config"):
                    print("Fatal Error: config.json is malformed and cannot be read!")
                    exit(1)
                pass
    except FileNotFoundError:
        pass
    
    # If file is corrupt or does not exist, silently return empty dictionary.
    return dict

def dumpConfig(config):
    with open(f"{configDir}/config.json", "w") as configFile:
        dump(config, configFile, indent = 4)

# Updates metadata (filename of associated model and checksum) for mold number whichMold
def updateMetaData(filename, checksum, configChecksum, whichMold):
    metadata = readJSON("config", "index")
    metadata["environment_checksum"] = f"{getEnvChecksum()}"
    metadata[f"{whichMold}"] = {"file" : filename, "data_checksum" : f"{checksum}", "config_checksum" : f"{configChecksum}"}
    with open(f"{configDir}/index.json",'w+') as indexFile:
        dump(metadata, indexFile, indent = 4)

# Returns a dictionary containing the requested spec limits for mold whichMold
def getSpec(whichMold):
    query = f"SELECT incubation_days_min, incubation_days_max, seed_days_min, seed_days_max, plate_days_min, plate_days_max FROM specs where spec_id = (SELECT spec_id from molds where mold_id = {whichMold});"
    rawData = SQLQuery(query)
    for d in rawData:
        spec = d
    return spec

# Generates appropriate queries for a trained model and pushes its results to the gp_predictions table in the SQL database
def pushModelResults(model, whichMold):
    spec = getSpec(whichMold)
    inc = list(range(spec["incubation_days_min"], spec["incubation_days_max"]))
    sed = list(range(spec["seed_days_min"], spec["seed_days_max"]))
    plt = list(range(spec["plate_days_min"], spec["plate_days_max"]))
    query = f"DELETE FROM gp_predictions WHERE mold_id = {whichMold}"
    SQLQuery(query)
    print(f"Uploading results to database... ", end="", flush=True)
    for i in inc:
        for s in sed:
            for p in plt:
                thisparams = [i,s,p]
                
                predicted_yield, predicted_stdev = model.predict([thisparams], return_std=True)
                query = f"INSERT INTO gp_predictions (mold_id, incubation_days, seed_days, plate_days, predicted_average_yield_per_liter, std_deviation) VALUES ({whichMold}, {i}, {s}, {p}, {predicted_yield[0]}, {predicted_stdev[0]})"
                SQLQuery(query)
    print("Success.")

# Pickles a trained model and dumps it to outputDir, then updates
# the corresponding mold's metadata accordingly
def dumpTrainedModel(filename, model, whichMold, checksum, configCheckum):
    with open(f"{outputDir}/{filename}" , "wb") as f:
        pickle.dump(model, f) 
    updateMetaData(filename, checksum, configCheckum, whichMold)
    pushModelResults(model, whichMold)

# Returns a cursor object for use in querying the SQL database, and a connection object for
# closing the connection once all queries are finished.
def getSQLCursor(user, password):
    try:
        # Host and DB hardcoded, these should never change.
        connection = connector.connect(user=user, password=password, host="localhost", database="mycology", autocommit=True)

    # Kill program on a connection error.
    except connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        exit(0)
    else:
        # Cursor will return list of dictionary objects when queried.
        cursor = connection.cursor(dictionary=True)
        return (connection, cursor)

# Creates a new connection to database, runs query, then terminates connection.
def SQLQuery(query):
    # Username and password hardcoded, these should never change.
    (connection, cursor) = getSQLCursor("python", "gaussianProcess")
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    connection.close()

    # Result is returned as a list of dicts
    return result

# Returns a configuration setting dictionary for mold number whichMold
def getConfig(config, whichMold):
    myConfig = config["default"]
    if f"{whichMold}" in config.keys():
        for f in config[f"{whichMold}"].keys():
            myConfig[f] = config[f"{whichMold}"][f]
    return myConfig

# Returns CRC32 checksum of the configuration settings for mold whichMold.
def getConfigChecksum(config, whichMold):
    configStr = dumps(getConfig(config, whichMold))
    return crc32(configStr.encode("utf-8"))

# Returns CRC32 checksum of data corresponding to mold number whichMold.
# Used to check if data has been updated to prevent needless retraining.
def getChecksum(whichMold):
    query = f"SELECT SUM(CRC32(lot_id)) from mold_lots WHERE mold_id = {whichMold};"
    rawData = SQLQuery(query)
    checksum = 0
    for d in rawData:
        checksum = d["SUM(CRC32(lot_id))"]
    return checksum   

# Returns CRC32 checksum of environment.
# test change 
def getEnvChecksum():
    configFiles = ["venv/requirements.txt", "venv/pyvenv.cfg"]
    sourceFiles = ["mycologyHelpers.py", "mycoTrainModels.py"]
    checksum = sum([int(crc32Opt(f"{configDir}/{f}"), 16) for f in configFiles]) + sum([int(crc32Opt(f"{configDir}/../source/{f}"), 16) for f in sourceFiles])
    return checksum