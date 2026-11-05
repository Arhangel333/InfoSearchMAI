from pymongo import MongoClient





client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]


doc = db.documents.count_documents({"text": {"$exists": False},"time": {"$exists": True}})

print(doc)
print(f"Удаляю поля в документах:")
result = db.documents.update_many(
    {"text": {"$exists": False},"time": {"$exists": True}},
    {"$unset": {"time": "", "text": "", "last_modified_ts": "", "char_count": "", "word_count": ""}}
)

print(f"Удалено полей в документах: {result.modified_count}")
print(f"Удалено полей в документах: {result}")