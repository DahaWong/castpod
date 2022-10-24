import json
from telegram.request import HTTPXRequest
from telegram.error import TelegramError


class MyRequest(HTTPXRequest):
    @staticmethod
    def parse_json_payload(payload: bytes):
        """Parse the JSON returned from Telegram.

        Tip:
            By default, this method uses the standard library's :func:`json.loads` and
            ``errors="replace"`` in :meth:`bytes.decode`.
            You can override it to customize either of these behaviors.

        Args:
            payload (:obj:`bytes`): The UTF-8 encoded JSON payload as returned by Telegram.

        Returns:
            dict: A JSON parsed as Python dict with results.

        Raises:
            TelegramError: If loading the JSON data failed
        """
        decoded_s = payload.decode("utf-8", "replace")
        print(decoded_s)
        try:
            print(json.loads(decoded_s))
            return json.loads(decoded_s)
        except ValueError as exc:
            print(exc)
            raise TelegramError("Invalid server response") from exc
