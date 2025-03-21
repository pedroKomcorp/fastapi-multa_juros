from fastapi import FastAPI, HTTPException
from datetime import datetime, date
import httpx

def safe_float(value):
    """Converte um valor para float, retornando 0 se a conversão falhar."""
    try:
        return round(float(value.replace(',', '.')), 2)
    except (ValueError, AttributeError):
        return 0.0

async def obter_taxa_selic(data_pagamento):
    url = f"https://fast-selic.onrender.com/selic/{data_pagamento}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            dados = response.json()
            return safe_float(dados.get("taxa_selic", 0))
        return None

app = FastAPI()

@app.get("/{valor}/{mes_ano}")
async def calcular_guia(valor: str, mes_ano: str):
    # Convertendo o valor
    valor = safe_float(valor)
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido.")
    
    # Convertendo a data de vencimento (assumindo sempre o dia 20 do mês informado)
    try:
        vencimento = datetime.strptime(f"20{mes_ano}", "%d%m%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use MMYYYY.")
    
    pagamento = date.today()
    
    if pagamento <= vencimento:
        dias_atraso = 0
        multa = 0.0
        juros = 0.0
    else:
        dias_atraso = (pagamento - vencimento).days
        multa_calculada = valor * 0.003 * dias_atraso
        multa = min(multa_calculada, valor * 0.20)
        
        taxa_selic = await obter_taxa_selic(pagamento)
        if taxa_selic is None:
            raise HTTPException(status_code=500, detail="Não foi possível obter a taxa SELIC.")
        
        juros = valor * taxa_selic
    
    total = valor + multa + juros
    
    return {
        "data_vencimento": vencimento.isoformat(),
        "valor_original": round(valor, 2),
        "multa": round(multa, 2),
        "juros": round(juros, 2),
        "valor_total": round(total, 2)
    }
