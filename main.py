from fastapi import FastAPI, HTTPException
from datetime import datetime, date
import httpx

def safe_float(value):
    """Converte um valor para float, retornando 0 se a conversão falhar."""
    try:
        return round(float(value.replace(',', '.')), 2)
    except (ValueError, AttributeError):
        return 0.0

async def obter_taxa_selic(mes_ano):
    url = f"https://fast-selic.onrender.com/selic/{mes_ano}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            dados = response.json()
            return safe_float(dados.get("taxa_selic", 0))
        return None

app = FastAPI()

@app.get("/{valor}/{data_vencimento}")
async def calcular_guia(valor: str, data_vencimento: str):
    # Convertendo o valor
    valor = safe_float(valor)
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido.")
    
    # Convertendo a data de vencimento (esperando ddmmyyyy)
    try:
        vencimento = datetime.strptime(data_vencimento, "%d%m%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use DDMMAAAA.")
    
    pagamento = date.today()
    
    if pagamento <= vencimento:
        dias_atraso = 0
        multa = 0.0
        juros = 0.0
    else:
        dias_atraso = (pagamento - vencimento).days
        multa_calculada = valor * 0.003 * dias_atraso
        multa = min(multa_calculada, valor * 0.20)
        
        # Obtendo a taxa SELIC baseada no mês e ano do pagamento
        mes_ano_selic = pagamento.strftime("%m%Y")
        taxa_selic = await obter_taxa_selic(mes_ano_selic)
        if taxa_selic is None:
            raise HTTPException(status_code=500, detail="Não foi possível obter a taxa SELIC.")
        
        juros = valor * taxa_selic
    
    total = valor + multa + juros
    
    return {
        "valor_original": round(valor, 2),
        "data_vencimento": vencimento.isoformat(),
        "data_pagamento": pagamento.isoformat(),
        "dias_atraso": dias_atraso,
        "multa": round(multa, 2),
        "juros": round(juros, 2),
        "valor_total": round(total, 2)
    }
