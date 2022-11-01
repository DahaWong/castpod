import re
from config import Wit
import magic
import httpx
from pprint import pprint
from pydub import AudioSegment
import json

API = "https://api.wit.ai/dictation"
ONE_MINUTE = 60 * 1000


async def generate(audio_path: str) -> str:
    # audio = AudioSegment.from_mp3(audio_path)
    # cut_audio = audio[:ONE_MINUTE]
    content_type = magic.from_file(audio_path, mime=True)
    token = Wit.client_tokens["jp"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    files = {"upload-file": open(audio_path, "rb")}
    async with httpx.AsyncClient() as client:
        res = await client.post(url=API, headers=headers, files=files, timeout=300)
    results = parse(res.text)
    text = "".join(
        map(
            lambda x: x["text"],
            filter(
                lambda y: y.get("is_final"),
                results,
            ),
        )
    )
    return text


def parse(text: str) -> list:
    chunks = text.split("\r\n")
    return [json.loads(chunk) for chunk in chunks]


"""
Response handling:
200
400
401
408
500
503
"""
