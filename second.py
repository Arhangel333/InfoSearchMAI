from bs4 import BeautifulSoup
import requests

url = 'https://www.cybersport.ru/search?search=dota%202%20'

response = requests.get(url)
soup = BeautifulSoup(response.text, 'lxml')


#def grep_http_from_searchpage()
pagestag = soup.find_all(class_='link_CocWY')
pages = pagestag


for i in pages:
    maxpage = i
    if(i['href'][0] == '/'):
        i['href'] = 'https://www.cybersport.ru' + i['href']
    print(i['href'])
    
print(f" The last is : \n \n \t {maxpage}")


