from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import requests
import re

app = FastAPI()


# ===== MODELO DO BODY (corrigido com alias) =====
class WebhookMessage(BaseModel):
    from_: str = Field(..., alias="from")
    body: str

    class Config:
        populate_by_name = True


@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


def extrair_valor(texto: str):
    match = re.search(r"(\d+[.,]?\d*)", texto)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body

    valor = extrair_valor(texto)

    resposta = "✅ Mensagem recebida!"
    if valor:
        resposta = f"💸 Anotei um gasto de R$ {valor:.2f}"

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
            print("Erro ao enviar WhatsApp:", e)

    return {
        "status": "ok",
        "received": {
            "from": telefone,
            "body": texto
        },
        "parsed": {
            "valor": valor
        }
    }
