import requests

def local_download(url):
    res = requests.get(url, allow_redirects=True)
    if res.status_code != 200:
        raise Exception("Error when downloading file.")
    file_path = f'public/audio/audio-temp.mp3'
    f = open(file_path, 'wb').write(res.content)
    return file_path

# local_download()