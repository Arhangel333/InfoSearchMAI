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
    #print(i)
    
#print(f" The last is : \n \n \t {maxpage}")
last = maxpage.text


pagecount = hrefcount = 0
currurl = url
lasturl = url + f'&page={last}'
#print(lasturl)
nextp = '1'

with open('pages.txt', 'a') as f:
    
    while ((currurl != lasturl) and (pagecount < 1000000)):
        response = requests.get(currurl)
        soup = BeautifulSoup(response.text, 'lxml')
        
        #print(currurl)      
        print(f'\rpagecount: {pagecount} | hrefs: {hrefcount}\r',end='', flush=True)
        
        pagestag = soup.find_all(class_='link_CocWY')
        
        pages = pagestag

        for i in pages:
            maxpage = i
            if(i['href'][0] == '/'):
                i['href'] = 'https://www.cybersport.ru' + i['href']
            
            f.write(i['href'])
            hrefcount+=1
            f.write('\n')
            


        #f.write(response.text)
        
        
        nextp = str(int(nextp) + 1)
        currurl = url + f'&page={nextp}'
        
        pagecount+=1