from pymongo import MongoClient
from config import mongodb_uri

client = MongoClient(mongodb_uri)
db = client.get_database()