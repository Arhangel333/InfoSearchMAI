from pymongo import MongoClient





client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]


doc = db.documents.find_one({"content": {"$exists": True}})
print(doc['content'])