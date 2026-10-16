from pymongo import MongoClient
import yaml
import os
import sys 
import datetime
import requests
from email.utils import format_datetime, parsedate_to_datetime
from datetime import datetime, timezone


LAST_MOD = "last_modified_ts"
v = 1
#db.documents.updateOne( {url: 'https://ria.ru'}, {$set: { time:'_now_', domen:'_domen_', content: '_html_'}})
#db.documents.updateOne( {url: 'https://ria.ru'}, {{ time:'_now_', last_update:'_time_'}})

def myprint(text):
    if(v):
        print(text)
        
def IsNeedUpdate(last_mod, doc):
    """ Сравнивает время обнавления сайта и в бд
    принимает с сайта в формате GMT и переводит в datatime
    из бд в формате datatime
    """
    if(last_mod):
        old_ts = doc.get(LAST_MOD)                               #time fom table
        lm_ts = parsedate_to_datetime(last_mod)                     #time from site

        if old_ts is None:
            print("Страницу надо скачать>>>")
            return True
        else:
            try:
                old_ts = datetime.fromisoformat(old_ts)
            except (TypeError, ValueError) as e:
                print(f"битая дата в БД {old_ts!r}: {e}")
                
                return True
            if old_ts.tzinfo is None:
                    old_ts = old_ts.replace(tzinfo=timezone.utc)
            if lm_ts > old_ts:
                myprint("Страница изменилась")
                return True
                # обновить html и last_modified_ts
    
        return False
        
    else:
        print(f"no datatime on {doc["url"]}")
        return False
    
def GetContent(doc):
    try:
        r = requests.get(doc["url"], timeout=5)
    except Exception as e:
        print(f"ошибка: {e}")
        return None 
    content = r.text
    return content
    
    
    
    
def main():
    if len(sys.argv) < 2:
        print("Usage: python <programm> <input.yaml> ")
        print("Example:")
        print("  python db_test.py config.yaml")   
        sys.exit(1)

    file = sys.argv[1]

    with open(file, "r") as f:
        yam = yaml.safe_load(f)

    db_client = yam["db"]["client"]
    db_login = yam["db"]["login"]
    db_pass = yam["db"]["password"]
    
    client = MongoClient(db_client)
    db = client["crawler"]
    """for docs in db.documents.find():
        print(docs) """
    #docs = list(db.documents.find()) #обязательно удалить эту шляпу ебаную которая как раз                                                                                 ...ебала мне RAM в 4 часа ночи
    
    #db.createtable("test")
    db2 = client["crawler"]  
    
    pid = os.getpid()
    
    start_point = int(yam["logic"]["start_with"])
    end_point = int(yam["logic"]["end_with"])
    try:
        counter = 0
        while(True):
            
            now = datetime.now()
            doc = db2.documents.find_one_and_update(
                {"content": {"$exists": False}, 
                 "time": {"$exists": False}},       # фильтр: нет content
                {"$set": {
                    "time": str(now),
                    LAST_MOD: str(now)
                }},
                return_document=True,
            ) 
            
            if doc is None:
                print("Больше нет задач")
                break

            content = GetContent(doc)
            
            if content is None:
                print(f"None content on url: {doc["url"]}")
            else:
                db2.documents.update_one({"_id": doc["_id"]}, {"$set": {LAST_MOD: str(now), "content": content}})
        
                       
            print(f"\r{pid}: Прогресс: {counter}", end="", flush=True)
            counter+=1
            if counter % yam["logic"]["check_interval"] == 0:
                with open(file, "r") as fl:
                    try:
                        yam = yaml.safe_load(fl)
                        if yam["logic"]["db_bot"] == "stop":
                            print(f"Получено прерывание из {file} Остановились на {counter}")
                            return counter
                    except (FileNotFoundError, yaml.YAMLError) as e:
                        print(f"не могу прочитать конфиг: {e}")
    
            if(counter < start_point):
                continue
            if(counter > end_point):
                print("End point reached")
                return 0

            
            if counter % 1000 == 0:
                print(f"Текущая позиция:{counter} продолжаем обкачку")
                
                
            
            
            
        
            myprint(doc["url"])
    except KeyboardInterrupt:
        print(f"Текущая позиция:{counter} Ctrl+C exit")
        return 0
            
        
if __name__ == "__main__":
    main()