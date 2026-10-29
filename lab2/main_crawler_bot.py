"""
sitemap_parser.py

Рекурсивно обходит sitemap (индекс → вложенные urlset'ы),
собирает все <loc> и пишет в файл, пока не наберёт лимит.
"""


#for selenium
from urllib.parse import urljoin, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
from pymongo import MongoClient
import pickle


#for sitemap
import sys
import yaml
import time
import gzip
import io
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from pymongo import MongoClient

v = 0 #verbose output
truework = 0

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


stats = {
    "files_ok": 0,
    "files_failed": 0,
    "urls_collected": 0,
}



HEADERS = {
    "User-Agent": "MaiSitemapParser/1.0 (+https://github.com/yourname; contact@example.com)",
    "Accept": "application/xml, text/xml, */*",
}

#++++++++++++++++++++++++++++  for selenium mode   +++++++++++++++++++++++++++++++++++++++++++++++++++++++

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

def myprint(text):
    if(v):
        print(text)
        
def same_host(url: str, domen: str) -> bool:
    myprint(f"check -----> {domen} in {url}")
    nowww = domen.replace("www.", "")
    return domen in url or nowww in url

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
                        if truework:
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
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def myprint(text):
    if(v):
        print(text)

def fetch(url: str, timeout: int = 30) -> bytes | None:
    """Скачивает URL, распаковывая gzip."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        content = r.content

        
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)

        return content
    except requests.RequestException as e:
        print(f"  [error] {url}: {e}", file=sys.stderr)
        stats["files_failed"] += 1
        return None


def parse_sitemap(content: bytes) -> tuple[list[str], list[str]]:
    """
    Парсит XML.
    Возвращает (urls, sub_sitemaps):
      urls — ссылки на страницы (<loc> внутри <url>)
      sub_sitemaps — ссылки на вложенные sitemap (<loc> внутри <sitemap>)
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [parse error] {e}", file=sys.stderr)
        return [], []

    tag = root.tag.split("}")[-1]   

    urls = []
    sub_sitemaps = []

    if tag == "urlset":
        for loc in root.findall(".//sm:url/sm:loc", NS):
            if loc.text:
                urls.append(loc.text.strip())

    elif tag == "sitemapindex":
        for loc in root.findall(".//sm:sitemap/sm:loc", NS):
            if loc.text:
                sub_sitemaps.append(loc.text.strip())

    else:
        print(f"  [warn] неизвестный корень: {tag}", file=sys.stderr)

    return urls, sub_sitemaps


def crawl_sitemap(start_url: str,
                  out_file,
                  db,
                  limit: int = 1_000_000,
                  delay: float = 0.3,
                  max_depth: int = 10) -> None:
    """
    Рекурсивно обходит sitemap, начиная с start_url.
    Пишет все найденные страницы в out_file.
    Останавливается при достижении limit.
    """
    
    queue = [(start_url, 0)]
    seen_sitemaps = set()   

    while queue:
        if stats["urls_collected"] >= limit:
            print(f"\nДостигнут лимит: {limit}")
            return

        url, depth = queue.pop(0)

        if url in seen_sitemaps:
            continue
        if depth > max_depth:
            print(f"  [skip] превышена глубина: {url}", file=sys.stderr)
            continue

        seen_sitemaps.add(url)
        print(f"[{stats['files_ok'] + stats['files_failed'] + 1}] "
              f"depth={depth} → {url}")

        content = fetch(url)
        if content is None:
            continue

        stats["files_ok"] += 1
        urls, sub_sitemaps = parse_sitemap(content)

        
        for page_url in urls:
            if stats["urls_collected"] >= limit:
                return
            if truework:
                db.documents.insert_one({"url": page_url})
            else:
                myprint(page_url + "\n")
                out_file.write(page_url + "\n")
            stats["urls_collected"] += 1

            if stats["urls_collected"] % 10_000 == 0:
                print(f"  ... собрано {stats['urls_collected']} URL")
                out_file.flush()

        print(f"  страниц: {len(urls)}, вложенных sitemap: {len(sub_sitemaps)}, "
              f"всего собрано: {stats['urls_collected']}")

        
        for sub in sub_sitemaps:
            if sub not in seen_sitemaps:
                queue.append((sub, depth + 1))

        time.sleep(delay)   


def main():
    if len(sys.argv) < 2:
        print("Usage: python <programm> <input.yaml> ")
        print("Example:")
        print("  python response_bot.py config.yaml")   
        sys.exit(1)

    file = sys.argv[1]

    with open(file, "r") as f:
        yam = yaml.safe_load(f)
        
    client = MongoClient(yam["db"]["client"])
    db = client["crawler"]


    if yam["logic"]["mode"] == "sitemap":
        
        domen = yam["logic"]["domen"]
        start_url = yam["logic"]["target"]
        out_path = yam["logic"]["output_file1"]
        try:
            limit = int(yam["logic"]["limit1"])
        except:
            limit = 1_000_000

        print(f"Start:  {start_url}")
        print(f"Output: {out_path}")
        print(f"Limit:  {limit}")
        print()

        t0 = time.time()
        
        
        


        with open(out_path, "w", encoding="utf-8") as out:
            crawl_sitemap(start_url, out, db, limit=limit)

        elapsed = time.time() - t0
        print()
        print("=" * 60)
        print(f"Готово за {elapsed:.1f} сек")
        print(f"Файлов обработано: {stats['files_ok']} (ошибок: {stats['files_failed']})")
        print(f"URL собрано:       {stats['urls_collected']}")
        print(f"Записано в:        {out_path}")
    else:
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        if yam["logic"]["mode"] == "selenium":
            
            driver = webdriver.Chrome(service=service, options=options)
            
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
            
            
            
            
            
            
            
            
            
            """ 
            url1 = yam["logic"]["target1"]
            myprint(f"{url1}")

            headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
            }
                
                
            try:
                driver.get(url1)
                
                
                x = "0"
                while(x=="0"):
                    html = driver.page_source   # ← готовый HTML после JS
                    myprint(html)
                    x = input(x)
                    
                    soup = BeautifulSoup(html, 'lxml')
                    pagestag = soup.find_all(attrs={"class": yam["logic"]["pagetag2"]})
                
                    for i in pagestag:
                        maxpage = i
                        if(i['href'][0] == '/'):
                            i['href'] = yam["logic"]["domen1"] + i['href']
                            myprint(i['href'])



            finally:
                driver.quit() """
            # end of selenium mode








if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    
    








    

    

