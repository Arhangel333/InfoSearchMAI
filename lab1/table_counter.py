import yaml
import os
import sys
import requests
from email.utils import format_datetime, parsedate_to_datetime
from datetime import datetime, timezone
import trafilatura
import time

from urllib.parse import urlparse
from pymongo import ReturnDocument

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]

# Список обязательных полей
required_fields = [
    "content", "text", "domen", "url", 
    "last_modified_ts", "time", "char_count", "word_count", "Unix_time"
]

# Формируем фильтр: каждое поле должно существовать ($exists: True)
query_filter = {field: {"$exists": True} for field in required_fields}

count = db.documents.count_documents(query_filter)
print(f"Найдено документов для обновления: {count}")

# 1. Находим все документы по нашему фильтру
docs = db.documents.find(query_filter, {"_id": 1})


x = input("Ready to update, continue? y/n")

if x !="y":
    exit()
    
processed = 0

for doc in docs:
    # 2. Атомарно получаем НОВЫЙ уникальный номер из счетчика
    counter = db.counters.find_one_and_update(
        {"_id": "doc_seq"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    new_id = counter["seq"]
    
    # 3. Обновляем ТЕКУЩИЙ документ, используя его _id
    db.documents.update_one(
        {"_id": doc["_id"]}, 
        {"$set": {"doc_id": new_id}}
    )
    
    processed += 1
    if processed % 1000 == 0:
        print(f"Обработано: {processed}/{count}")

print(f"Готово! Присвоено doc_id: {processed}")

db.documents.create_index("doc_id", unique=True)
print(f"Готово! Создан индекс!")