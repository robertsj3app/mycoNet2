from msilib.schema import Error
import numpy
from mysql import connector
from mysql.connector import errorcode

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
    cursor = connection.cursor()
    query = f"SELECT incubation_days, seed_days, plate_days, yield_per_liter FROM `mold_lots` WHERE mold_id = {whichMold} AND incubation_days > 0 AND seed_days > 0 AND plate_days > 0 AND discarded = 0 and facility = \"Lenoir\" ORDER BY `mold_lots`.`mfg_date` ASC;"
    cursor.execute(query)

    for (incubation_days, seed_days, plate_days, yield_per_liter) in cursor:
        dataset.append([incubation_days, seed_days, plate_days, yield_per_liter])

    cursor.close()
    connection.close()

print(numpy.array(dataset))