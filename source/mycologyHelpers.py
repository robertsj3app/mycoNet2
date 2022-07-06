from mysql import connector
from mysql.connector import errorcode
import json
from json.decoder import JSONDecodeError
import pickle

def readMetaData():
    metadata = {}
    try:
        with open('output/index.json','r') as indexFile:
            try:
                metadata = json.load(indexFile)
            except JSONDecodeError:
                pass
    except FileNotFoundError:
        pass
    return metadata

def updateMetaData(filename, checksum, whichMold):
    metadata = readMetaData()
    metadata[f"{whichMold}"] = {"file" : filename, "checksum" : f"{checksum}"}
    with open('output/index.json','w+') as indexFile:
        json.dump(metadata, indexFile, indent = 4)

def dumpTrainedModel(filename, model, whichMold, checksum):
    with open(f"output/{filename}" , "wb") as f:
        pickle.dump(model, f) 
    updateMetaData(filename, checksum, whichMold)

def getSQLCursor(user, password):
    try:
        connection = connector.connect(user=user, password=password, host="localhost", database="mycology")
    except connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        exit(0)
    else:
        cursor = connection.cursor(dictionary=True)
        return (connection, cursor)

def SQLQuery(query):
    (connection, cursor) = getSQLCursor("python", "gaussianProcess")
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    return result

def getChecksum(whichMold):
    query = f"SELECT SUM(CRC32(lot_id)) from mold_lots WHERE mold_id = {whichMold};"
    rawData = SQLQuery(query)
    checksum = 0
    for d in rawData:
        checksum = d["SUM(CRC32(lot_id))"]
    return checksum    