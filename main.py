from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import re
import requests
from supabase import create_client

app = FastAPI()

# =============================
# SUPABASE
# =============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =============================
# MODELO DE ENTRADA
# =============================
class WebhookMessage(BaseModel):
    from_: str = Field(..., alias="from")
    body: str


# =============================
# HOME
# =============================
@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


# =============================
# INTERPRETA TEXTO
# =============================
def interpretar_texto(texto: str):
    texto_lower = texto.lower()

    # captura valor
    valor_match = re.search(r"(\d+[.,]?\d*)", texto_lower)
    valor = float(valor_match.group(1).replace(",", ".")) if valor_match else None

    tipo = "despesa"
    if any(p in texto_lower for p in ["ganhei", "recebi", "salário", "salario"]):
        tipo = "receita"

    categorias = [
        "mercado", "roupa", "comida", "aluguel",
        "uber", "gasolina", "internet", "luz", "agua"
    ]

    categoria = next((c for c in categorias if c in texto_lower), "outros")

    return {
        "valor": valor,
        "tipo": tipo,
        "categoria": categoria
    }


# =============================
# WEBHOOK
# =============================
@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body

    parsed = interpretar_texto(texto)

    # salva no banco
    if supabase and parsed["valor"] is not None:
        supabase.table("movimentos").insert({
            "telefone": telefone,
            "tipo": parsed["tipo"],
            "categoria": parsed["categoria"],
            "valor": parsed["valor"],
            "texto_original": texto
        }).execute()

    # resposta WhatsApp (opcional)
    ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
    ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")

    if ULTRA_INSTANCE and ULTRA_TOKEN:
        try:
            requests.post(
                f"https://api.ultramsg.com/{ULTRA_INSTANCE}/messages/chat",
                data={
                    "token": ULTRA_TOKEN,
                    "to": telefone,
                    "body": "✅ Anotado! Já registrei esse lançamento."
                },
                timeout=10
            )
        except:
            pass

    return {
        "status": "ok",
        "received": {
            "from": telefone,
            "body": texto
        },
        "parsed": parsed
    }
