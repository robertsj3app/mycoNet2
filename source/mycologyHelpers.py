# myclogyHelpers.py
# A group of functions used to facilitiate interfacing with the mycology SQL database.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com

from mysql import connector
from mysql.connector import errorcode
from json import load, dump
from json.decoder import JSONDecodeError
import pickle
from os import path, makedirs
import sys
from datetime import date, datetime

# Define directory all outputs (index file and trained models) go to. Defined relative to location of script. 
outputDir = path.join(path.dirname(__file__), "../output") 

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
def readMetaData():
    metadata = {}
    try:
        with open(f"{outputDir}/index.json",'r') as indexFile:
            try:
                metadata = load(indexFile)
            except JSONDecodeError:
                pass
    except FileNotFoundError:
        pass
    
    # If file is corrupt or does not exist, silently return empty dictionary.
    # All models will be retrained and a properly formatted index.json will be created.
    return metadata

# Updates metadata (filename of associated model and checksum) for mold number whichMold
def updateMetaData(filename, checksum, whichMold):
    metadata = readMetaData()
    metadata[f"{whichMold}"] = {"file" : filename, "checksum" : f"{checksum}"}
    with open(f"{outputDir}/index.json",'w+') as indexFile:
        dump(metadata, indexFile, indent = 4)

# Pickles a trained model and dumps it to outputDir, then updates
# the corresponding mold's metadata accordingly
def dumpTrainedModel(filename, model, whichMold, checksum):
    with open(f"{outputDir}/{filename}" , "wb") as f:
        pickle.dump(model, f) 
    updateMetaData(filename, checksum, whichMold)

# Returns a cursor object for use in querying the SQL database, and a connection object for
# closing the connection once all queries are finished.
def getSQLCursor(user, password):
    try:
        # Host and DB hardcoded, these should never change.
        connection = connector.connect(user=user, password=password, host="localhost", database="mycology")

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

# Returns CRC32 checksum of data corresponding to mold number whichMold.
# Used to check if data has been updated to prevent needless retraining.
def getChecksum(whichMold):
    query = f"SELECT SUM(CRC32(lot_id)) from mold_lots WHERE mold_id = {whichMold};"
    rawData = SQLQuery(query)
    checksum = 0
    for d in rawData:
        checksum = d["SUM(CRC32(lot_id))"]
    return checksum    