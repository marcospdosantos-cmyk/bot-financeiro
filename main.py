from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import re
import requests
from supabase import create_client
from datetime import datetime, date, timedelta

app = FastAPI()

# =============================
# SUPABASE
# =============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# MODELO
# =============================
class WebhookMessage(BaseModel):
    from_: str = Field(..., alias="from")
    body: str


@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


# =============================
# EXTRAÇÃO DE DADOS
# =============================
def extrair_data(texto: str):
    texto = texto.lower()
    hoje = date.today()

    if "hoje" in texto:
        return hoje
    if "ontem" in texto:
        return hoje - timedelta(days=1)

    match = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?", texto)
    if match:
        d, m, a = match.groups()
        try:
            return date(int(a) if a else hoje.year, int(m), int(d))
        except:
            return None

    return None


def interpretar_texto(texto: str):
    texto_lower = texto.lower()

    valor_match = re.search(r"(\d+[.,]?\d*)", texto_lower)
    valor = float(valor_match.group(1).replace(",", ".")) if valor_match else None

    tipo = "despesa"
    if any(p in texto_lower for p in ["ganhei", "recebi", "salário", "salario"]):
        tipo = "receita"

    categoria = "outros"
    categorias = {
        "mercado": "mercado",
        "supermercado": "mercado",
        "roupa": "roupas",
        "almoço": "alimentação",
        "janta": "alimentação",
        "comida": "alimentação",
        "aluguel": "moradia",
        "luz": "contas",
        "água": "contas",
        "internet": "contas",
        "gasolina": "transporte",
        "uber": "transporte"
    }

    for palavra, cat in categorias.items():
        if palavra in texto_lower:
            categoria = cat
            break

    return {
        "valor": valor,
        "tipo": tipo,
        "categoria": categoria,
        "data": extrair_data(texto)
    }


# =============================
# WEBHOOK
# =============================
@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body.strip()

    parsed = interpretar_texto(texto)

    resposta = "Não entendi sua mensagem 🤔"

    if parsed["valor"] is not None:
        supabase.table("movimentos").insert({
            "telefone": telefone,
            "tipo": parsed["tipo"],
            "categoria": parsed["categoria"],
            "valor": parsed["valor"],
            "texto_original": texto,
            "criado_em": parsed["data"] or datetime.utcnow()
        }).execute()

        resposta = (
            f"✅ Anotado!\n"
            f"{parsed['tipo'].capitalize()} de R$ {parsed['valor']:.2f}\n"
            f"Categoria: {parsed['categoria']}"
        )

    # envia resposta via WhatsApp
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
        except:
            pass

    return {
        "status": "ok",
        "received": {"from": telefone, "body": texto},
        "parsed": parsed
    }
