from pymongo import MongoClient





client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]


doc = db.documents.count_documents({
    "text": "429 Too Many Requests\nYou have sent too many requests in a given amount of time."
})

target_text = "429 Too Many Requests\nYou have sent too many requests in a given amount of time."
print(doc)

result = db.documents.update_many(
    {"text": target_text},
    {"$unset": {"time": "", "text": "", "last_modified_ts": "", "char_count": "", "word_count": ""}}
)

print(f"Удалено полей в документах: {result.modified_count}")
