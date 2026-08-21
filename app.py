import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

# Ladda miljövariabler från .env-filen i samma mapp
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Stoppa direkt om nyckeln saknas
if not DISCORD_WEBHOOK_URL:
    raise RuntimeError("DISCORD_WEBHOOK_URL saknas i .env-filen!")

app = FastAPI()

class Message(BaseModel):
    text: str

@app.post("/send")
def send_to_discord(msg: Message):
    payload = {"content": msg.text}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=500, detail="Kunde inte skicka till Discord")
    
    return {"status": "skickat"}
