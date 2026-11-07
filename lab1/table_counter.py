from pymongo import MongoClient
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





client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]
count = 0

while True:
    # Шаг 1: найти документ

    doc = db.documents.find_one({"domen": {"$exists": False}, "url": {"$exists": True}})
    if not doc:
        break
    

    
    domen = urlparse(doc["url"]).netloc
    
    db.documents.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "domen": domen
        }}
    )

    count +=1
    print(f"Progress: {count}\t{doc.get('url')}")

""" for d in doc:
    html = d.get("content")
    full_size += len(html)
    html_count +=1
print(f"{full_size / html_count}\n {html_count}") """

