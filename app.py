import json
import os
from dataclasses import dataclass
from typing import Mapping

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Ladda miljövariabler från .env-filen i samma mapp.
load_dotenv()


@dataclass(frozen=True)
class WebhookConfig:
    webhooks: dict[str, str]
    default_channel: str | None
    legacy_url: str | None


def load_webhook_config(env: Mapping[str, str]) -> WebhookConfig:
    """Läs namngivna webhooks och bevara stöd för DISCORD_WEBHOOK_URL."""
    raw_webhooks = env.get("DISCORD_WEBHOOKS", "").strip()
    legacy_url = env.get("DISCORD_WEBHOOK_URL", "").strip() or None
    default_channel = env.get("DISCORD_DEFAULT_CHANNEL", "").strip() or None
    webhooks: dict[str, str] = {}

    if raw_webhooks:
        try:
            parsed = json.loads(raw_webhooks)
        except json.JSONDecodeError as exc:
            raise RuntimeError("DISCORD_WEBHOOKS måste vara giltig JSON") from exc

        if not isinstance(parsed, dict) or not parsed:
            raise RuntimeError("DISCORD_WEBHOOKS måste vara ett JSON-objekt med minst en kanal")

        for channel, url in parsed.items():
            if not isinstance(channel, str) or not channel or channel != channel.strip():
                raise RuntimeError("Ogiltigt kanalalias i DISCORD_WEBHOOKS")
            if not isinstance(url, str) or not url.strip():
                raise RuntimeError(f"Webhook-URL saknas för kanalalias {channel!r}")
            webhooks[channel] = url.strip()

    if not webhooks and not legacy_url:
        raise RuntimeError("Ange DISCORD_WEBHOOKS eller DISCORD_WEBHOOK_URL i .env")
    if default_channel and default_channel not in webhooks:
        raise RuntimeError("DISCORD_DEFAULT_CHANNEL måste finnas i DISCORD_WEBHOOKS")
    if webhooks and not default_channel and not legacy_url:
        raise RuntimeError("DISCORD_DEFAULT_CHANNEL krävs för namngivna webhooks")

    return WebhookConfig(webhooks, default_channel, legacy_url)


CONFIG = load_webhook_config(os.environ)

app = FastAPI(
    title="Discord Proxy",
    description="Internt API för att skicka notifieringar via Discord",
    version="1.1.0",
    root_path="/api/discord",
)


class Message(BaseModel):
    text: str
    kanal: str | None = None


def webhook_for_channel(kanal: str | None) -> str:
    if kanal is not None:
        webhook_url = CONFIG.webhooks.get(kanal)
        if webhook_url is None:
            raise HTTPException(status_code=400, detail="Okänd Discord-kanal")
        return webhook_url

    if CONFIG.default_channel is not None:
        return CONFIG.webhooks[CONFIG.default_channel]
    assert CONFIG.legacy_url is not None
    return CONFIG.legacy_url


@app.post("/send")
def send_to_discord(msg: Message):
    webhook_url = webhook_for_channel(msg.kanal)
    try:
        response = requests.post(webhook_url, json={"content": msg.text}, timeout=10)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Kunde inte kontakta Discord") from exc

    if response.status_code not in (200, 204):
        raise HTTPException(status_code=502, detail="Kunde inte skicka till Discord")

    return {"status": "skickat"}
