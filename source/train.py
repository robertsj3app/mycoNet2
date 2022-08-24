# train.py
# Trains GaussianProcessRegressor for each mold defined in MySQL database.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com

from GPFactory import GPFactory
from DBConnection import DBConnection
from mycologyHelpers import getDateTime, toggleLog

def trainOne(which):
    fact = GPFactory()
    fact.trainModel(which)

def train():

    # Turn on logging.
    toggleLog()
    fact = GPFactory()
    conn = DBConnection("python", "gaussianProcess")

    # Get list of mold ids from database.
    query = "SELECT mold_id from molds WHERE 1"
    mold_ids = []
    rawData = conn.SQLQuery(query)
    for d in rawData:
        mold_ids.append(d["mold_id"])
    
    print(f"Beginning training on {getDateTime()}")
    for i in mold_ids:
        fact.trainModel(i)
    toggleLog()

train()