import requests
import json

root = 'https://itunes.apple.com/search?'
endpoints = {
  'search_podcast': 'media=podcast&country=CN&term=',
}

def search(keyword:str):
  res = requests.get(f"{root}{endpoints['search_podcast']}{keyword}")
  results = res.json()['results']
  return results 


