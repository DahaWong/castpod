import requests

def local_download(url, file_name):
    try:
        res = requests.get(url, allow_redirects=True)
        if res.status_code != 200:
            raise Exception
        file_path = f'public/audio/{file_name}.mp3'
        with open(file_path, 'wb').write(res.content):
            return file_path
    except:
        print(f"Error when fetching file {file_name}")
