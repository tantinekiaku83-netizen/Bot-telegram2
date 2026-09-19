# -*- coding: utf-8 -*-
import os
import asyncio
import logging
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from telegram import Bot

# ================= CONFIGURAÇÃO (RAILWAY & ENV) =================
TOKEN = os.getenv("TELEGRAM_TOKEN", "8864077129:AAGynp2700ocgTeh-0aWoTkD-UwE95_jeuQ")
CHAT_ID = os.getenv("CHAT_ID", "-1004424432080")
API_URL = os.getenv("API_URL", "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("SUPREMO-G2")

bot = Bot(token=TOKEN)

state = {
    "history": [],
    "last_id": None,
    "waiting": False,
    "target": None,
    "gale_step": 0,    # 0 = SG, 1 = G1, 2 = G2
    "wins": 0,
    "wins_sg": 0,      # Greens diretos + Empate no SG
    "wins_g1": 0,      # Greens no Gale 1 + Empate no G1
    "wins_g2": 0,      # Greens no Gale 2 + Empate no G2
    "wins_tie": 0,     # Histórico de Empates
    "losses": 0,
    "streak": 0,
    "streak_loss": 0,
    "pause_until": None,
    "msg_placar": None,
    "msg_analise": None,
    "msg_gale": None,
    "last_reset_day": None
}

# ================= BANCO DE ESTRATÉGIAS TURBINADO (G2) =================
PADROES = [
    # ALTERNÂNCIAS (XADREZ)
    {"seq": ["🔵","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔵","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔴","🔵","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔵","🔴","🔵"], "sinal": "🔴"},
    
    # QUEBRAS DE TENDÊNCIA (ANTI-SURF)
    {"seq": ["🔵","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔵","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔴","🔴","🔴","🔴"], "sinal": "🔵"},
    
    # BLOCOS E ESPELHAMENTOS
    {"seq": ["🔵","🔵","🔴","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔴","🔵","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔴","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔵","🔵","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔴","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔵","🔴","🔴"], "sinal": "🔵"},
    
    # ESTRATÉGIAS DE REPETIÇÃO
    {"seq": ["🔵","🔵","🔵","🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔴","🔴","🔴","🔵","🔵","🔵"], "sinal": "🔴"},

    # ================= NOVOS PADRÕES EXCLUSIVOS (G2) =================
    # ESCADAS DE TRANSIÇÃO (1x2x3 / 3x2x1)
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔵", "🔵", "🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},

    # SIMETRIA CENTRAL (1x3x1 E 2x1x2)
    {"seq": ["🔵", "🔴", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔵", "🔴"], "sinal": "🔵"},
    {"seq": ["🔵", "🔵", "🔴", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔵", "🔴", "🔴"], "sinal": "🔵"},

    # REVERSÃO DE BLOCO QUADRUPLO E TRIPLO (4x4 E 3x3x3)
    {"seq": ["🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴"], "sinal": "🔵"},

    # EXAUSTÃO EXTREMA DE MESA (6 E 7 SEGUIDAS)
    {"seq": ["🔵", "🔵", "🔵", "🔵", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔴", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔵", "🔵", "🔵", "🔵", "🔵", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔴", "🔴", "🔴", "🔴", "🔴"], "sinal": "🔵"},

    # ESPELHAMENTO DUPLO (2x2x2)
    {"seq": ["🔵", "🔵", "🔴", "🔴", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔵", "🔵", "🔴", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 1*2*3*1*1 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 4*1*1*4 =================
    {"seq": ["🔵", "🔵", "🔵", "🔵", "🔴", "🔵", "🔴", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔴", "🔴", "🔵", "🔴", "🔵", "🔵", "🔵", "🔵"], "sinal": "🔴"},

    # ================= PADRÃO 2*1*2*1*2 =================
    {"seq": ["🔵", "🔵", "🔴", "🔵", "🔵", "🔴", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔵", "🔴", "🔴", "🔵", "🔴", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 1*2*4*2*1 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 3*3 =================
    {"seq": ["🔵", "🔵", "🔵", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔴", "🔵", "🔵", "🔵"], "sinal": "🔴"},

    # ================= PADRÃO 1*2*1 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 4*3*2*1 =================
    {"seq": ["🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},

    # ================= PADRÃO 3*3*2*3*3 =================
    {"seq": ["🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 3*3*2*3 =================
    {"seq": ["🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵", "🔵", "🔵"], "sinal": "🔴"},

    # ================= RAMPA 1*2*3*4 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵"], "sinal": "🔴"},

    # ================= RAMPA 1*2*3*2*1 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},

    # ================= RAMPA 1*2*3*4*3*2*1 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},

    # ================= RAMPA 1*2*3*4*5*4*3*2*1 =================
    {"seq": ["🔵", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔴", "🔴", "🔵"], "sinal": "🔴"},
    {"seq": ["🔴", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔴", "🔴", "🔵", "🔵", "🔵", "🔵", "🔴", "🔴", "🔴", "🔵", "🔵", "🔴"], "sinal": "🔵"},

    # ================= PADRÃO 3*1*1*3 =================
    {"seq": ["🔵", "🔵", "🔵", "🔴", "🔵", "🔴", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔴", "🔵", "🔴", "🔵", "🔵", "🔵"], "sinal": "🔴"},

    # ================= PADRÃO 2*1*1*2 =================
    {"seq": ["🔵", "🔵", "🔴", "🔵", "🔴", "🔴"], "sinal": "🔵"},
    {"seq": ["🔴", "🔴", "🔵", "🔴", "🔵", "🔵"], "sinal": "🔴"},
]

# ================= FUNÇÕES DE ENVIO E MENSAGENS =================
async def send_msg(text):
    try:
        m = await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        return m.message_id
    except Exception as e:
        log.error(f"Erro ao enviar mensagem: {e}")
        return None

async def delete_msg(mid):
    if mid:
        try: 
            await bot.delete_message(chat_id=CHAT_ID, message_id=mid)
        except Exception: 
            pass

async def enviar_placar():
    if state["msg_placar"]: 
        await delete_msg(state["msg_placar"])
    
    total_jogadas = state["wins"] + state["losses"]
    assertividade = (state["wins"] / total_jogadas * 100) if total_jogadas > 0 else 0.0

    texto = (
        f"📊 <b>PLACAR DO DIA 🛸</b>\n\n"
        f"✅ <b>Vitórias:</b> {state['wins']}\n"
        f"❌ <b>Derrotas:</b> {state['losses']}\n\n"
        
        f"<b>SG:</b> {state['wins_sg']}\n"
        f"<b>G1:</b> {state['wins_g1']}\n"
        f"<b>G2:</b> {state['wins_g2']}\n\n"
        
    )
    
    state["msg_placar"] = await send_msg(texto)

async def processar_resultado(cor):
    if cor == "🟡" or cor == state["target"]:
        state["wins"] += 1
        state["streak"] += 1
        state["streak_loss"] = 0 
        
        # Registra o tipo correto do Green (Empate conta como Green no passo atual)
        if state["gale_step"] == 0:
            state["wins_sg"] += 1
            tipo = "SG"
        elif state["gale_step"] == 1:
            state["wins_g1"] += 1
            tipo = "G1"
        else:
            state["wins_g2"] += 1
            tipo = "G2"
        
        if cor == "🟡":
            state["wins_tie"] += 1
            msg_vitoria = (f"🟠 <b>EMPATE PROTETOR!</b>\n"
                           f"❇️❇️❇️❇️❇️❇️❇️❇️\n❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥𝗣𝗔𝗚𝗢𝗢𝗢 NO EMPATE!🔥\n\n"
                           f"🛸 TOMAA!!! {state['streak']} GREENS SEGUIDOS 🚀")
        else:
            msg_vitoria = (f"❇️❇️❇️❇️❇️❇️❇️❇️\n❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥𝗣𝗔𝗚𝗢𝗢𝗢!🔥 {tipo}\n\n"
                           f"🛸 TOMAA!!! {state['streak']} GREENS SEGUIDOS 🚀")
        
        await send_msg(msg_vitoria)
        await delete_msg(state["msg_analise"])
        await delete_msg(state["msg_gale"])
        state.update({"waiting": False, "gale_step": 0, "msg_analise": None, "msg_gale": None})
        await enviar_placar()

    elif state["gale_step"] == 0:
        state["gale_step"] = 1
        await delete_msg(state["msg_gale"])
        state["msg_gale"] = await send_msg("⚠️ <b>VAMOS PARA O GALE 1</b>")
    
    elif state["gale_step"] == 1:
        state["gale_step"] = 2
        await delete_msg(state["msg_gale"])
        state["msg_gale"] = await send_msg("⚠️⚠️ <b>VAMOS PARA O GALE 2</b>")
    
    else:
        state["losses"] += 1
        state["streak"] = 0
        state["streak_loss"] += 1
        
        await send_msg("❌ <b>LOSS, A MESA NÃO RESPEITOU!</b>")
        await delete_msg(state["msg_analise"])
        await delete_msg(state["msg_gale"])
        state.update({"waiting": False, "gale_step": 0, "msg_analise": None, "msg_gale": None})

        if state["streak_loss"] >= 2:
            state["pause_until"] = datetime.now() + timedelta(minutes=10)
            await send_msg("🛑 <b>PAUSA DE SEGURANÇA (10 MIN)</b>\n2 Reds seguidos. Preservando a banca!")
            state["streak_loss"] = 0
            
        await enviar_placar()

# ================= REQUISIÇÃO DA API =================
def fetch_api_data():
    req = urllib.request.Request(
        API_URL, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Cache-Control": "no-cache"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
    except urllib.error.HTTPError as e:
        log.warning(f"API retornou erro HTTP {e.code}: {e.reason}")
    except Exception as e:
        log.warning(f"Aviso de conexão com a API: {e}")
    return None

# ================= LOOP PRINCIPAL =================
async def main():
    log.info(f"BlackG2 iniciado com sucesso. Total de padrões carregados: {len(PADROES)}")
    await enviar_placar()
    
    while True:
        try:
            # RESET AUTOMÁTICO DO PLACAR ÀS 00:00 (HORÁRIO DE ANGOLA - UTC+1)
            hoje_angola = datetime.now(timezone(timedelta(hours=1))).date()
            if state["last_reset_day"] is None:
                state["last_reset_day"] = hoje_angola
            elif state["last_reset_day"] != hoje_angola:
                # 1. GERAR E ENVIAR O RELATÓRIO COMPLETO DO DIA ANTERIOR
                data_str = state["last_reset_day"].strftime("%d/%m/%Y")
                total_greens = state["wins"]
                total_reds = state["losses"]
                total_jogadas = total_greens + total_reds
                
                assertividade = (total_greens / total_jogadas * 100) if total_jogadas > 0 else 0.0

                relatorio_dia = (
                    f"📊 <b>RELATÓRIO DO DIA ANTERIOR ({data_str})</b>\n\n"
                    f"✅ <b>Vitórias:</b> {total_greens}\n"
                    f"❌ <b>Derrotas:</b> {total_reds}\n\n"
                    f"<b>SG:</b> {state['wins_sg']}\n"
                    f"<b>G1:</b> {state['wins_g1']}\n"
                    f"<b>G2:</b> {state['wins_g2']}\n\n"
                
                    f"🔄 <i>Placar zerado para as operações de hoje!</i>"
                )
                await send_msg(relatorio_dia)

                # 2. ZERAR AS VARIÁVEIS PARA O NOVO DIA
                state["wins"] = 0
                state["wins_sg"] = 0
                state["wins_g1"] = 0
                state["wins_g2"] = 0
                state["wins_tie"] = 0
                state["losses"] = 0
                state["streak"] = 0
                state["streak_loss"] = 0
                state["last_reset_day"] = hoje_angola
                
                await enviar_placar()

            if state["pause_until"]:
                if datetime.now() < state["pause_until"]:
                    await asyncio.sleep(5)
                    continue
                else:
                    state["pause_until"] = None
                    await send_msg("🔄 <b>RETOMANDO ANÁLISES!</b>\nPausa encerrada.")

            data = await asyncio.to_thread(fetch_api_data)
            if data:
                d = data.get("data", data)
                if isinstance(d, list) and len(d) > 0:
                    d = d[0]
                
                if isinstance(d, dict):
                    rid = d.get("id") or d.get("gameId")
                    
                    if rid and rid != state["last_id"]:
                        state["last_id"] = rid
                        res_block = d.get("result", {})
                        res_raw = res_block.get("outcome") if isinstance(res_block, dict) else d.get("outcome")
                        
                        cor = {
                            "PlayerWon": "🔵", "Jogador": "🔵", "Player": "🔵", "PLAYER": "🔵",
                            "BankerWon": "🔴", "Bancao": "🔴", "Banker": "🔴", "BANKER": "🔴",
                            "Tie": "🟡", "Empate": "🟡", "TIE": "🟡"
                        }.get(res_raw)
                        
                        if cor:
                            if cor != "🟡":
                                state["history"].append(cor)
                                state["history"] = state["history"][-30:]
                            
                            if state["waiting"]:
                                await processar_resultado(cor)
                            else:
                                found = False
                                for p in PADROES:
                                    if len(state["history"]) >= len(p["seq"]) and state["history"][-len(p["seq"]):] == p["seq"]:
                                        state["target"] = p["sinal"]
                                        state["waiting"] = True
                                        state["gale_step"] = 0
                                        
                                        if state["msg_analise"]:
                                            await delete_msg(state["msg_analise"])
                                            state["msg_analise"] = None

                                        entrada = (f"🚀 <b>ENTRADA CONFIRMADA</b>\n\n"
                                                   f"Apostar: {p['sinal']}\n"
                                                   f"Proteção: 🟡 Empate\n"
                                                   f"Limite: 2 Gales")
                                        await send_msg(entrada)
                                        found = True
                                        break
                                
                                if not found and not state["msg_analise"]:
                                    state["msg_analise"] = await send_msg("🔍 <b>Analisando padrões...</b>")

        except Exception as e:
            log.error(f"Erro crítico no loop principal: {e}")
            
        await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Aplicação encerrada manualmente.")

# CRIADOR : CRISTÓVÃO MIGUEL 🇧🇷🇦🇴
# WHATSAPP: +244951868182
