#! /bin/bash
python3 search_bot.py config.yaml

docker run -d \
  --name crawler-mongo \
  -p 27017:27017 \
  -v mongo_data:/data/db \
  mongo:7