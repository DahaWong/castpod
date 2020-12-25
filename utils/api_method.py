import requests
import json

# 换成 google podcast ，spotify 是否可行
root = 'https://itunes.apple.com/search?'
endpoints = {
  'search_podcast': 'media=podcast&country=CN&term=',
}

def search(keyword:str):
  res = requests.get(f"{root}{endpoints['search_podcast']}{keyword}")
  results = res.json()['results']
  return results 

# def spotify_search(keyword:str):
#   headersAPI = {
#     'accept': 'application/json',
#     'Authorization': 'Bearer '+ 'BQC6unM9WV8GYYIrRhIpR-uJaQ9FLP7KF2xTlIanMXkxi5K1ii5O7ES0VxB3SVdacnvEGGOPqHcl5Hx9LKE',
#   }
#   response = requests.get(
#     'https://api.spotify.com/v1/search', 
#     headers=headersAPI, 
#     params=(
#       ('q', keyword), 
#       ('type', 'show')
#     ),
#     verify=True
#   )
#   print(response.json())

# spotify_search('一天世界')

