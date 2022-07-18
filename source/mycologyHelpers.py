# myclogyHelpers.py
# A group of miscellaneous functions to be used in other scripts.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com

from json import load, dump, dumps
from json.decoder import JSONDecodeError
from os import path, makedirs
import sys
from datetime import date, datetime
from zlib import crc32

# Define directories for output and configuration files. Defined relative to location of script. 
outputDir = path.join(path.dirname(__file__), "../output") 
configDir = path.join(path.dirname(__file__), "../config")

# Variable to control whether logging is enabled or not
logState = False

# Define logger class that dumps stdout to logfile (named based on date of instantiation) as well as terminal.
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        if not path.exists(f"{outputDir}/logs"):
            makedirs(f"{outputDir}/logs")
        self.log = open(f"{outputDir}/logs/training_log_{date.today()}.txt", "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message) 

    def flush(self):
        self.terminal.flush()
        self.log.flush()
        pass

# Toggle whether logging is active. Date of instantiating the logger is used until logging toggled off and on again.
def toggleLog():
    global logState
    if logState == False:
        sys.stdout = Logger()
        logState = True
    else:
        sys.stdout = sys.__stdout__
        logState = False

# Optimized zlib.crc32 for checksumming files in chunks
def crc32Opt(fileName):
    with open(fileName, 'rb') as fh:
        hash = 0
        while True:
            s = fh.read(65536)
            if not s:
                break
            hash = crc32(s, hash)
        return "%08X" % (hash & 0xFFFFFFFF)

# Return string showing current date and time
def getDateTime():
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    date = now.date()
    return f"{date} at {time}"

# Reads json file named filename.json in directory whichDir into a dictionary.
def readJSON(whichDir, filename):
    dict = {}
    try:
        with open(f"{whichDir}/{filename}.json",'r') as file:
            try:
                dict = load(file)
            except JSONDecodeError:

                # Program won't work without config.json
                if(filename == "config"):
                    print("Fatal Error: config.json is malformed and cannot be read! Correct or delete file to restore functionality.")
                    exit(1)
                pass
    except FileNotFoundError:
        pass
    
    # If file is corrupt or does not exist, silently return empty dictionary.
    return dict

# Creates default configuration file if none exists.
# Fixes errors in configuration file.
def initConfig():
    defaultConfig = {
        "credentials": {
            "username" : "python",
            "password" : "gaussianProcess"
        },
        "default": {
            "n_restarts_optimizer" : 100,
            "n_minimum_data_points" : 10,
            "additional_training_features" : [],
            "conditionals" : ["facility != 'Willow Street'", "facility != 'Unknown'", "plug_type != 'Unknown'"]
        },
    }
    existingConfig = readJSON(configDir, "config")
    if existingConfig == {}:
        print("No configuration file found. Generating default configuration file...")
        dumpConfig(defaultConfig)
    else:
        if (not "credentials" in list(existingConfig.keys())
        or not "username" in list(existingConfig["credentials"].keys())
        or not "password" in list(existingConfig["credentials"].keys())):
            print("Warning: Configuration missing credentials, fixing...")
            existingConfig["credentials"] = defaultConfig["credentials"]
        if (not "default" in list(existingConfig.keys()) 
        or not "n_restarts_optimizer" in list(existingConfig["default"].keys())
        or not "n_minimum_data_points" in list(existingConfig["default"].keys())
        or not "additional_training_features" in list(existingConfig["default"].keys())
        or not "conditionals" in list(existingConfig["default"].keys())):
            print("Warning: Configuration missing default training behavior, fixing...")
            existingConfig["default"] = defaultConfig["default"]
        dumpConfig(existingConfig)

# Dumps dictionary config to config file.
def dumpConfig(config):
    with open(f"{configDir}/config.json", "w") as configFile:
        dump(config, configFile, indent = 4)

# Returns CRC32 checksum of dictionary dict.
def dictChecksum(dict):
    return crc32(dumps(dict).encode("utf-8"))

# Returns CRC32 checksum of environment.
def envChecksum():
    configFiles = ["venv/requirements.txt", "venv/pyvenv.cfg"]
    sourceFiles = ["GPFactory.py", "DBConnection.py", "mycologyHelpers.py"]
    checksum = -1
    try:
        checksum = sum([int(crc32Opt(f"{configDir}/{f}"), 16) for f in configFiles]) + sum([int(crc32Opt(f"{configDir}/../source/{f}"), 16) for f in sourceFiles])
    except FileNotFoundError:
        print("Fatal Error: Files necessary for environment not found!")
        exit(1)
    return checksum