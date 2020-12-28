import requests
from config import cuttly_token

def shorten(url):
    api = f'https://cutt.ly/api/api.php?key={cuttly_token}&short={url}'
    data = requests.get(api).json()['url']
    if data["status"] == 7:
        shortened_url = data["shortLink"]
        return shortened_url
    else:
        raise Exception("Error when shortening URL")
        print(r.text)
        return url