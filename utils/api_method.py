import requests
import json

root = 'https://itunes.apple.com/search?'
endpoints = {
  'search_podcast': 'media=podcast&term=',
}

def search(keyword:str):
  res = requests.get(f"{root}{endpoints['search_podcast']}{keyword}")
  data = res.json()
  name = [item["collectionName"] for item in data["results"]]