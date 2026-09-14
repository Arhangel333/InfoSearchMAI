from bs4 import BeautifulSoup
import requests

url = 'https://www.cybersport.ru/search?search=dota%202%20'

response = requests.get(url)
soup = BeautifulSoup(response.text, 'lxml')

pagestag = soup.find(class_='root_eDhkj')
pages = pagestag.children
maxpage = pages

for i in pages:
    maxpage = i
    print(i)
    
print(f" The last is : \n \n \t {maxpage}")
last = maxpage.text


count = 0
currurl = url
lasturl = url + f'&page={last}'
#print(lasturl)
nextp = '226'

with open('pages.txt', 'a') as f:
    
    while ((currurl != lasturl) and (count < 1000000)):
        response = requests.get(currurl)
        soup = BeautifulSoup(response.text, 'lxml')
        
        print(currurl)      
        print(f'Current pages count: {count}\r', end='', flush=True) 
        f.write(response.text)
        
        
        nextp = str(int(nextp) + 1)
        currurl = url + f'&page={nextp}'
        
        count+=1