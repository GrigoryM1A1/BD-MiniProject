import certifi
import os
from pymongo import *
from pymongo.database import *
from dotenv import load_dotenv
import pprint

load_dotenv('.env')

username: str = os.getenv("MONGODB_USERNAME")
password: str = os.getenv("MONGODB_PASSWORD")


class MongoConnection:
    def __init__(self):
        self.uri = f"""mongodb+srv://{username}:{password}@hotelscluster.53jqjfk.mongodb.net/?retryWrites=true&w=majority"""
        self.client: MongoClient = MongoClient(self.uri, tlsCAFile=certifi.where())
        self.db: Database = self.client["HotelsDB"]
        self.customers: Collection = self.db["Customers"]
        self.hotels: Collection = self.db["Hotels"]
        self.rooms: Collection = self.db["Rooms"]


if __name__ == '__main__':
    mongo = MongoConnection()
