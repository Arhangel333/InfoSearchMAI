from pymongo import MongoClient
import yaml
import os
import sys 
import datetime
import requests
from email.utils import format_datetime, parsedate_to_datetime
from datetime import datetime, timezone
import trafilatura
import time



pid = os.getpid()
LAST_MOD = "last_modified_ts"
TERMINAL_LOGS = f"{pid}terminal_log.txt"
v = 0
true_work = 1
logs = 1
terminal_loging = 0


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
        url = doc["url"]
        r = requests.get(doc["url"], timeout=5)
        # ПРОВЕРКА КОДА ОТВЕТА
        if r.status_code != 200:
            with open(TERMINAL_LOGS, "a") as f:
                f.write(f"Ошибка {r.status_code} для {url} время: {datetime.now()}\n")
    except Exception as e:
        print(f"ошибка: {e}")
        return None 
    content = r.text
    return content



def GetTextFromHTML(doc):
    char_count = 0
    word_count = 0
                
                
                
    url = doc.get('url')
    myprint(url)
    

    
    html = GetContent(doc)           
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
                    f.write(f"{datetime.now()}\n\n")
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
    
    
    
    
    
            
            
    return html, text, char_count, word_count, success
    
    
def PasteTextToDB(db, doc, html, text, char_count, word_count, now):
    if true_work:
        return db.documents.update_one({"_id": doc["_id"]}, {"$set": {LAST_MOD: str(now), "content": html, "text": text, "char_count": char_count, "word_count": word_count}})
    else:
        return 0
    
    
    
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
                                                          
    
    #db.createtable("test")
    db = client["crawler"]  
    
    
    
    start_point = int(yam["logic"]["start_with"])
    end_point = int(yam["logic"]["end_with"])
    try:
        counter = 0
        db_success = 0
        db_errors = 0
        success_count = 0
        extract_text_error = 0
        continue_work = 1
        last_count_db = 0
        myprint("starting cycle")
        while(True):
            
            now = datetime.now()
            doc = db.documents.find_one_and_update(
                {"content": {"$exists": False}, 
                 "time": {"$exists": False}},       # фильтр: нет content
                {"$set": {
                    "time": str(now)
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
                
                html, text, char_count, word_count, success = GetTextFromHTML(doc)
                if success:
                    success_count += 1
                else:
                    extract_text_error +=1
                    continue
                
                db_paste_success = PasteTextToDB(db, doc, html, text, char_count, word_count, now)
                if not db_paste_success:
                    db_errors +=1
                    myprint("Error on writing to database")
                else:
                    db_success +=1
                #db.documents.update_one({"_id": doc["_id"]}, {"$set": {LAST_MOD: str(now), "text": text}})
        
            with open(TERMINAL_LOGS, "a") as f:
                f.write(f"\n{pid}: Прогресс: {counter} время: {datetime.now() - now}\n")         
            #print(f"{pid}: Прогресс: {counter}\n", end="", flush=True)
            
            if not terminal_loging:
                print(f"{pid}: Прогресс: {counter} время: {datetime.now() - now}")  
            
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
                
                
            
            
            
            time.sleep(1)
            myprint(doc["url"])
    except KeyboardInterrupt:
        print(f"Текущая позиция:{counter} Ctrl+C exit")
        print(f"Successfully extracted: {success_count}, Extract errors: {extract_text_error}\n")
        print(f"Successfully wrote: {db_success}, Write on db errors: {db_errors}\n")
        return 0
            
        
if __name__ == "__main__":
    main()