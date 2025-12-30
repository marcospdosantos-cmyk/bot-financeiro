from fastapi import FastAPI
from pydantic import BaseModel
import os
import re
import requests

app = FastAPI()


# ===== MODELO DO BODY (faz o Swagger mostrar o Request Body) =====
class WebhookMessage(BaseModel):
    from_: str
    body: str


@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


# ===== FUNÇÃO AUXILIAR PARA EXTRAIR VALOR E TEXTO =====
def extrair_gasto(texto: str):
    texto = texto.lower()

    # tenta achar número (50, 25.90 etc)
    match = re.search(r"(\d+[.,]?\d*)", texto)

    valor = None
    if match:
        valor = float(match.group(1).replace(",", "."))

    return valor


@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body

    valor = extrair_gasto(texto)

    # resposta padrão
    resposta = "✅ Mensagem recebida!"

    if valor:
        resposta = f"💸 Anotei um gasto de R$ {valor:.2f}"
    else:
        resposta = "📩 Recebi sua mensagem, mas não identifiquei um valor."

    # variáveis de ambiente (Render)
    ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
    ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")

    # envia resposta pro WhatsApp (se estiver configurado)
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
