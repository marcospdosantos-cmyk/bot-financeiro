from fastapi import FastAPI
from pydantic import BaseModel
import os
import re
from supabase import create_client

app = FastAPI()

# =============================
# Conexão com Supabase
# =============================
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# =============================
# Modelo do webhook
# =============================
class WebhookMessage(BaseModel):
    from_: str | None = None
    body: str | None = None


# =============================
# Função que interpreta a mensagem
# =============================
def interpretar_mensagem(texto: str):
    texto = texto.lower()

    resultado = {
        "tipo": None,
        "valor": None,
        "categoria": None,
        "descricao": texto,
        "dia": None
    }

    # Extrair valor numérico
    numeros = re.findall(r"\d+", texto)
    if numeros:
        resultado["valor"] = int(numeros[0])

    # Identificar tipo
    if any(p in texto for p in ["gastei", "paguei", "comprei"]):
        resultado["tipo"] = "gasto"
    elif any(p in texto for p in ["guardar", "economizar", "juntar"]):
        resultado["tipo"] = "meta"
    elif any(p in texto for p in ["pagar", "lembrete", "vencer", "dia"]):
        resultado["tipo"] = "lembrete"

    # Categorias simples
    categorias = [
        "mercado", "luz", "água", "agua",
        "internet", "aluguel", "viagem",
        "cartão", "cartao", "escola"
    ]

    for cat in categorias:
        if cat in texto:
            resultado["categoria"] = cat
            break

    return resultado


# =============================
# Rota principal (teste)
# =============================
@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Bot financeiro rodando 🚀"
    }


# =============================
# Webhook (WhatsApp / testes)
# =============================
@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body or ""

    interpretado = interpretar_mensagem(texto)

    if telefone and texto:
        supabase.table("mensagens").insert({
            "telefone": telefone,
            "texto": texto,
            "tipo": interpretado["tipo"],
            "valor": interpretado["valor"],
            "categoria": interpretado["categoria"]
        }).execute()

    return {
        "status": "ok",
        "interpretado": interpretado
    }
