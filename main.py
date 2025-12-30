from fastapi import FastAPI, Request
import os
import requests
from supabase import create_client

app = FastAPI()

# conexão com o Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")


# ✅ ROTA DE TESTE (essa evita erro 404)
@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Bot financeiro rodando 🚀"
    }


# ✅ ROTA DO WEBHOOK (cole aqui)
@app.post("/webhook")
async def webhook(req: Request):
    try:
        data = await req.json()
    except:
        data = {}

    texto = data.get("body", "")
    telefone = data.get("from", "")

    if texto and telefone:
        supabase.table("mensagens").insert({
            "telefone": telefone,
            "texto": texto
        }).execute()

    return {
        "status": "ok",
        "recebido": data
    }
