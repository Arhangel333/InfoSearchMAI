import yaml
import time
import sys
import requests
import pickle
from urllib.parse import urljoin, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
from pymongo import MongoClient

options = Options()
#options.add_argument("--headless=new")   # без окна
options.add_argument("--no-sandbox")     # для Docker/Linux
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--user-data-dir=/mnt/c/Users/Me/AppData/Local/Google/Chrome/User Data")

#driver = webdriver.Chrome(options=options)


service = Service(
    log_output="chromedriver.log",
    service_args=["--verbose"]
)
driver = webdriver.Chrome(service=service, options=options)


v = 0 #verbose output

def myprint(text):
    if(v):
        print(text)
        
def same_host(url: str, domen: str) -> bool:
    myprint(f"check -----> {domen} in {url}")
    nowww = domen.replace("www.", "")
    return domen in url or nowww in url

if(len(sys.argv)<=1):
    print("Usage: <programm> <input.yaml> ")
    exit(0)

file = sys.argv[1]

myprint(file)










def scroll_and_collect(
    driver,
    db: str,
    link_selector: str = "a[href]",
    step_px: int = 600,          # сколько пикселей за раз
    pause: float = 1.0,          # пауза между скроллами
    max_steps: int = 100,        # предохранитель от бесконечности
    domen: str = "",            # для фильтрации чужих ссылок
    max_urls: int = 1000000,         # не больше 1 000 000 на финальном парсе
    max_scroll: int = 0,
) -> list[str]:
    """
    Плавно прокручивает страницу и собирает все ссылки.
    Возвращает список уникальных абсолютных URL.
    """


    collected: set[str] = set()
    y = 0
    last_height = 0
    stuck_count = 0

    for step in range(max_steps):
        if len(collected) > max_urls:
            myprint("1.000.000 COLLECTED")
            break
        myprint(f"step {step}")
        # 1. прокрутить вниз на step_px
        y += step_px
        if max_scroll:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        else:
            driver.execute_script(f"window.scrollTo(0, {y});")
        time.sleep(pause)

        # 2. текущая высота страницы
        height = driver.execute_script("return document.body.scrollHeight")

        # 3. собрать ссылки из DOM прямо сейчас
        elements = driver.find_elements(By.CSS_SELECTOR, link_selector)
        # берём только те, что появились после прошлого шага
        elements = elements[len(collected):]
        new_count = 0
        for el in elements:
            href = el.get_attribute("href")
            myprint(href)
            if not href:
                myprint("no href found")
                continue
            # фильтр мусора
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                myprint("href contains trash")
                continue
            # фильтр по домену (если задан)
            myprint(domen)
            if same_host(href, domen):
                if href not in collected:
                    collected.add(href)
                    with open("part_output.txt", "a") as pf:
                        pf.write(href + "\n")
                        db.documents.insert_one({"url": href, "domen": domen})
                    new_count += 1
                else:
                    myprint(f"href is in the collection already ({href})")
            else:
                myprint(f"bad host ({href})")
        else:
            myprint("No elements collected")
        print(f"[step {step+1}] y={y}, height={height}, "
              f"ссылок всего={len(collected)}, новых={new_count}")

        # 4. проверяем, растёт ли страница
        if height == last_height and new_count == 0:
            stuck_count += 1
            if stuck_count >= 3:   # три шага подряд без изменений — вниз
                # скролл — в самый низ
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause)
                if stuck_count >= 5:   # 5 шагов подряд без изменений — стоп
                    print("Контент больше не подгружается")
                    break
        else:
            stuck_count = 0
        last_height = height

        # 5. дошли до конца страницы
        if y >= height:
            # последний скролл — в самый низ
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            # ещё раз собираем
            for el in driver.find_elements(By.CSS_SELECTOR, link_selector):
                href = el.get_attribute("href")
                if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
                    if not domen or same_host(href, domen):
                        collected.add(href)
            break
    else:
        myprint("step break")
    return sorted(collected)


  
with open(file, "r") as f:
    yam = yaml.safe_load(f)
    myprint(yam)
    
    url0 = yam["logic"]["target"]
    myprint(f"{url0}")
    
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
}
     
    
    try:
        db_client = yam["db"]["client"]
        client = MongoClient(db_client)
        db = client["crawler"]
        driver.get(yam["logic"]["target"])
        chunk = scroll_and_collect(
            driver,
            db, 
            link_selector=yam["logic"]["el_signature"],
            step_px=600,          # сколько пикселей за раз
            pause= 1.0,          # пауза между скроллами
            max_steps= 10000000,        # предохранитель от бесконечности
            domen= yam["logic"]["domen"],            # для фильтрации чужих ссылок
            max_urls=1000001,
            max_scroll = yam["logic"]["scroll_to_the_end_true"],
        )
        
        myprint(chunk)
        with open("output.txt", "w", encoding="utf-8") as f:
            for url in chunk:
                f.write(url + "\n")
        
    finally:
        driver.quit()


