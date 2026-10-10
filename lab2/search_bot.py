import sys
import yaml
import requests
import pickle
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

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


v = 1 #verbose output

def myprint(text):
    if(v):
        print(text)

if(len(sys.argv)<=1):
    print("Usage: <programm> <input.yaml> ")
    exit(0)

file = sys.argv[1]

myprint(file)

    
with open(file, "r") as f:
    yam = yaml.safe_load(f)
    myprint(yam)
    
    url1, url2 = yam["logic"]["target1"], yam["logic"]["target2"]
    myprint(f"{url1}, {url2}")
    
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
}
    
    
    try:
        driver.get(url2)
        
        
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
        driver.quit()
