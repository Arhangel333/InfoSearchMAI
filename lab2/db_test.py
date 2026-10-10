from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["crawler"]
db.documents.insert_one({"url": "https://ria.ru"})

#db.documents.updateOne( {url: 'https://ria.ru'}, {$set: { time:'_now_', domen:'_domen_', content: '_html_'}})
#db.documents.updateOne( {url: 'https://ria.ru'}, {{ time:'_now_', last_update:'_time_'}})