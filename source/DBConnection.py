# DBConnection.py
# Defines DBConnection class used to interfact with local MySQL database.
# Author: Jeremy Roberts
# Contact: Jeremy.Roberts@stallergenesgreer.com

from mysql import connector
from mysql.connector import errorcode
from typing_extensions import Self

class DBConnection(object):
    __db_connection = None
    __db_cursor = None

    def __init__(self: Self, username: str, password: str):
        (self.__db_connection, self.__db_cursor) = self.__getSQLCursor(username, password)

    # Returns a cursor object for use in querying the SQL database, and a connection object for
    # closing the connection once all queries are finished.
    def __getSQLCursor(self: Self, username: str, password: str):
        try:

            # Host and DB hardcoded, these should never change.
            connection = connector.connect(user=username, password=password, host="localhost", database="mycology", autocommit=True)

        # Kill program on a connection error.
        except connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Fatal Error: Database access denied. Check your username and password.")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Fatal Error: Database does not exist.")
            else:
                print(err)
            exit(0)
        else:

            # Cursor will return list of dictionary objects when queried.
            cursor = connection.cursor(dictionary=True)
            return (connection, cursor)

    # Run query against database.
    def SQLQuery(self: Self, query: str):
        self.__db_cursor.execute(query)
        result = self.__db_cursor.fetchall()

        # Result is returned as a list of dicts.
        return result

