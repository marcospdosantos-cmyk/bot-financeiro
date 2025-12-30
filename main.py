from fastapi import FastAPI, Request
import os
import requests
from supabase import create_client

app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")

@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Bot financeiro rodando 🚀"
    }

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    texto = data.get("body", "")
    telefone = data.get("from", "")

    # salva mensagem
    supabase.table("mensagens").insert({
        "telefone": telefone,
        "texto": texto
    }).execute()

    # resposta simples
    resposta = "✅ Mensagem recebida! Já anotei aqui."

    requests.post(
        f"https://api.ultramsg.com/{ULTRA_INSTANCE}/messages/chat",
        data={
            "token": ULTRA_TOKEN,
            "to": telefone,
            "body": resposta
        }
    )

    return {"status": "ok"}
