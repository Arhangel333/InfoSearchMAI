from pymongo import MongoClient
import yaml
import sys 
import datetime
import requests
from email.utils import format_datetime, parsedate_to_datetime
from datetime import datetime, timezone
import trafilatura
import time


LAST_MOD = "last_modified_ts"
DOCUMENT_COUNT_LIMIT = 1000000
v = 0
logs = 1
true_work = 1

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
    
    
#это было для обновленния
def UpdateScript(doc, db2, now):
    try:
        r = requests.get(doc["url"], timeout=5)
    except Exception as e:
        print(f"ошибка: {e}")
        #continue                 <<<<================================= это не забыть
    content = r.text
    if(IsNeedUpdate(r.headers.get("last-modified"), doc)): #если было обновлено после даты в документе то подгружаем новый текст страницы
        if 'time' in doc:
            db2.documents.update_one({"_id": doc["_id"]}, {"$set": {LAST_MOD: str(now), "content": content}})
        else:#если впервые заносим в таблицу html
            db2.documents.update_one({"_id": doc["_id"]}, {"$set": {"time": str(now), LAST_MOD: str(now), "content": content}})
            
    return




def GetTextFromHTML(doc):
    
    url = doc.get('url')
    myprint(url)
    content_html = doc.get('content')

    
    html = content_html            
    text = trafilatura.extract(html)
    
    if text:
            # Размер в символах (с пробелами)
            char_count = len(text)
            # Количество слов
            word_count = len(text.split())
            success = 1
            
            if logs:
                with open("test_text_from_html.txt", "a") as f:
                    f.write("\n\n")
                    f.write(url)
                    f.write(":\n")
                    f.write(text)
                    f.write(f"\nСимволов: {char_count}")
                    f.write(f"\nСлов: {word_count}")
                
    else:
        success = 0       
        if logs:
            with open("test_text_from_html.txt", "a") as f:
                f.write(url)
                f.write(":\n")
                
                f.write("Не удалось извлечь текст")
    
    
    
    
    
            
            
    return text, char_count, word_count, success
    
    
    
def PasteTextToDB(db, doc, text, char_count, word_count, now):
    if true_work:
        return db.documents.update_one({"_id": doc["_id"]}, {"$set": {LAST_MOD: str(now), "text": text, "char_count": char_count, "word_count": word_count}})
    
    
    
    
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
    collection = db[yam["db"]["collection"]]
 
    
    start_point = int(yam["logic"]["start_with"])
    end_point = int(yam["logic"]["end_with"])
    
    success_count = 0
    extract_text_error = 0
    continue_work = 1
    try:
        while(continue_work):
            counter = 0#счетчик обработки
            myprint("Starting find")
            for doc in db.documents.find({"content": {"$exists": True}, "text": {"$exists": False}}, {"url": 1, "content": 1}):      #db.documents.find({"html": {"$exists": False}})
                
                
                print(f"\rПрогресс: {counter}", end="", flush=True)
                counter+=1
                if(counter < start_point):
                    continue
                if(counter > DOCUMENT_COUNT_LIMIT):
                    print("DOCUMENT COUNT LIMIT reached")
                    continue_work = 0
                    break
                
                
                if counter % 1000 == 0:
                    print(f"Текущая позиция:{counter} продолжаем обкачку")
                    
                    
                now = datetime.now()
                
                
                
                
                
                
                text, char_count, word_count, success = GetTextFromHTML(doc)
                 
                if success:
                    success_count += 1
                else:
                    extract_text_error +=1
            
            
                PasteTextToDB(db, doc, text, char_count, word_count, now)
            
            
            
            
            
            
            
            
            
                myprint(doc["url"])
            time.sleep(1)
        
        print(f"Successfully extracted: {success_count}, Extract errors: {extract_text_error}\n")
    except KeyboardInterrupt:
        print(f"Successfully extracted: {success_count}, Extract errors: {extract_text_error}\n")
        print(f"Текущая позиция:{counter} Ctrl+C exit")
        return 0
            
        
if __name__ == "__main__":
    main()