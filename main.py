from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests
from supabase import create_client

app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class WebhookMessage(BaseModel):
    from_: str | None = None
    body: str | None = None


@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Bot financeiro rodando 🚀"
    }


@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body

    if telefone and texto:
        supabase.table("mensagens").insert({
            "telefone": telefone,
            "texto": texto
        }).execute()

    return {
        "status": "ok",
        "recebido": {
            "from": telefone,
            "body": texto
        }
    }
