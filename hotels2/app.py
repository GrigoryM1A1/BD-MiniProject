from flask import Flask
from hotels2 import create_app
import pymongo
from server.dbOperations import *


app = create_app()


if __name__ == '__main__':
    #app.run(debug=True)
    pass