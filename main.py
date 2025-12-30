from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import requests
import re

app = FastAPI()


class WebhookMessage(BaseModel):
    from_: str = Field(..., alias="from")
    body: str

    class Config:
        populate_by_name = True


@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


def extrair_info(texto: str):
    texto = texto.lower()

    # valor
    valor = None
    match = re.search(r"(\d+[.,]?\d*)", texto)
    if match:
        valor = float(match.group(1).replace(",", "."))

    # tipo
    tipo = "indefinido"
    if any(p in texto for p in ["gastei", "comprei", "paguei", "pagar"]):
        tipo = "despesa"
    elif any(p in texto for p in ["recebi", "ganhei", "entrou"]):
        tipo = "receita"

    # categoria simples
    categorias = {
        "mercado": ["mercado", "supermercado"],
        "roupas": ["roupa", "roupas"],
        "alimentação": ["comida", "lanche", "almoço", "jantar"],
        "transporte": ["uber", "ônibus", "gasolina", "combustível"],
        "contas": ["luz", "água", "internet", "aluguel"]
    }

    categoria = None
    for cat, palavras in categorias.items():
        if any(p in texto for p in palavras):
            categoria = cat
            break

    return {
        "valor": valor,
        "tipo": tipo,
        "categoria": categoria
    }


@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body

    info = extrair_info(texto)

    resposta = "📩 Mensagem recebida."

    if info["valor"]:
        if info["tipo"] == "despesa":
            resposta = f"💸 Anotei um gasto de R$ {info['valor']:.2f}"
        elif info["tipo"] == "receita":
            resposta = f"💰 Registrei uma entrada de R$ {info['valor']:.2f}"
        else:
            resposta = f"💬 Vi o valor R$ {info['valor']:.2f}, mas não entendi se é gasto ou entrada."

        if info["categoria"]:
            resposta += f" na categoria *{info['categoria']}*."

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
            print("Erro WhatsApp:", e)

    return {
        "status": "ok",
        "received": {
            "from": telefone,
            "body": texto
        },
        "parsed": info
    }
