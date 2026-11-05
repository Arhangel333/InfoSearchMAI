from pymongo import MongoClient


url = "https://ria.ru/20260417/es-2087571421.html"


client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]


doc = db.documents.find_one({"url": url})
print(doc)
""" doc = db.documents.count_documents({"text": {"$exists": False},"time": {"$exists": True}})

print(doc)
print(f"Удаляю поля в документах:")
result = db.documents.update_many(
    {"text": {"$exists": False},"time": {"$exists": True}},
    {"$unset": {"time": "", "text": "", "last_modified_ts": "", "char_count": "", "word_count": ""}}
)

print(f"Удалено полей в документах: {result.modified_count}")
print(f"Удалено полей в документах: {result}") """