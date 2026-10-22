#! /bin/bash


#source ../venv/bin/activate 
#python3 search_bot.py config.yaml

python3 main_crawler_bot.py config.yaml




#docker run -d \
#  --name crawler-mongo \
#  -p 27017:27017 \
#  -v mongo_data:/data/db \
#  mongo:7

docker start crawler-mongo

#docker exec -it crawler-mongo sh
#mongosh
#use crawler



#db.documents.countDocuments({ "content": { "$exists": false } })
#db.documents.findOne({},{"content": 0})
 
python3 db_load_html.py 2config.yaml &