from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]

# Фильтр: только документы БЕЗ doc_id
query_filter = {"doc_id": {"$exists": False}}

count = db.documents.count_documents(query_filter)
print(f"Найдено документов без doc_id: {count}")

if count == 0:
    print("Все документы уже пронумерованы.")
    exit()

x = input("Продолжить? y/n: ")
if x.lower() != "y":
    exit()

processed = 0
for doc in db.documents.find(query_filter, {"_id": 1}):
    # Атомарно получаем следующий ID из того же счетчика
    counter = db.counters.find_one_and_update(
        {"_id": "doc_seq"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    new_id = counter["seq"]
    
    db.documents.update_one(
        {"_id": doc["_id"]}, 
        {"$set": {"doc_id": new_id}}
    )
    
    processed += 1
    if processed % 1000 == 0:
        print(f"Обработано: {processed}/{count}")

print(f"Готово! Присвоено doc_id: {processed}")