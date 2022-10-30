import asyncio
import base64
import json
import httpx
import config
from uuid import UUID, uuid4
from manifest import manifest

# import config

root = "https://api.spotify.com/v1"
REDIRECT_URL = f"https://t.me/{manifest.bot_id}?start=spotify"


async def get_access_token() -> str:
    payload = {"grant_type": "client_credentials"}
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(config.client_id+':'+ config.client_secret, 'utf-8')).decode('utf-8')}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            url="https://accounts.spotify.com/api/token", headers=headers, data=payload
        )
    token = json.loads(res.content)["access_token"]
    # print(token)
    return token


def make_authorize_url(scope: str, state: UUID):
    # TODO: use pickle persistence
    url = (
        "https://accounts.spotify.com/authorize?"
        f"response_type=code&"
        f"client_id={config.client_id}&"
        f"scope={scope}&"
        f"redirect_uri={REDIRECT_URL}&"
        f"state={state}"
    )
    return url


def make_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Host": "api.spotify.com",
    }


async def search_podcast(keywords: str):
    token = await get_access_token()
    headers = make_headers(token)
    async with httpx.AsyncClient() as client:
        res = await client.get(
            url=f"{root}/search?q={keywords}&type=show&market=US&limit=25",
            headers=headers,
        )
    code = res.status_code
    CODES = httpx.codes
    print(code)
    if code == CODES.OK:
        return res.content
    elif code == CODES.UNAUTHORIZED:
        pass
    elif code == CODES.TOO_MANY_REQUESTS:
        pass
    else:
        pass


async def lookup_podcast(id: str):
    token = await get_access_token()
    headers = make_headers(token)
    async with httpx.AsyncClient() as client:
        res = await client.get(
            url=f"{root}/shows/{id}?market=US",
            headers=headers,
        )
    if res.status_code == httpx.codes.OK:
        podcast = json.loads(res.content)
        return podcast["name"], podcast["images"][0]["url"]


async def lookup_episode(id: str):
    token = await get_access_token()
    headers = make_headers(token)
    async with httpx.AsyncClient() as client:
        res = await client.get(
            url=f"{root}/episodes/{id}?market=US",
            headers=headers,
        )
    if res.status_code == httpx.codes.OK:
        episode = json.loads(res.content)
        podcast = episode["show"]
        return podcast["name"], podcast["images"][0]["url"]
