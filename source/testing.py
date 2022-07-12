from msilib.schema import Error
import numpy
from mysql import connector
from mysql.connector import errorcode
import json
import mycologyHelpers as mH

# from json.decoder import JSONDecodeError

# metadata = {}
# with open('output/index.json','r+') as indexFile:
#     try:
#         metadata = json.load(indexFile)
#     except JSONDecodeError:
#         pass

# metadata["mold2"] = "test3"

# with open('output/index.json','w+') as indexFile:
#     json.dump(metadata, indexFile, indent = 4)

whichMold ="1"
dataset = []

try:
    connection = connector.connect(user="python", password="gaussianProcess", host="localhost", database="mycology")
except connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
else:
    cursor = connection.cursor(dictionary=True)
    query = f"SELECT SUM(CRC32(lot_id)) from mold_lots WHERE mold_id = {whichMold};"
    cursor.execute(query)
    result = cursor.fetchall()
    checksum = 0
    for d in result:
        checksum = d["SUM(CRC32(lot_id))"]

    cursor.close()
    connection.close()

print(mH.getSpec(1))