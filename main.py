from fastapi import FastAPI, Request
import os
import requests

app = FastAPI()


@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    telefone = data.get("from", "")
    texto = data.get("body", "")

    # resposta padrão
    resposta = "✅ Mensagem recebida! Já anotei aqui."

    # (opcional) enviar resposta via WhatsApp
    ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
    ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")

    if ULTRA_INSTANCE and ULTRA_TOKEN and telefone:
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
        except:
            pass  # evita erro se API cair

    return {
        "status": "ok",
        "received": {
            "from": telefone,
            "body": texto
        }
    }
