from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import requests

app = FastAPI()


class WebhookMessage(BaseModel):
    from_: str = Field(alias="from")
    body: str


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Bot financeiro rodando 🚀"
    }


@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body

    resposta = "✅ Mensagem recebida! Já anotei aqui."

    ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
    ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")

    if ULTRA_INSTANCE and ULTRA_TOKEN:
        try:
            requests.post(
                f"https://api.ultramsg.com/{ULTRA_INSTANCE}/messages/chat",
                data={
                    "token": ULTRA_TOKEN,
                    "to": telefone,
                    "body": resposta
                },
                timeout=10
            )
        except Exception as e:
            print("Erro ao enviar resposta:", e)

    return {
        "status": "ok",
        "received": {
            "from": telefone,
            "body": texto
        }
    }

