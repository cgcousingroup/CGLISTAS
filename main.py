import logging
import asyncio
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatMemberHandler,
    ContextTypes,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
import json
import os

# =============== CONFIGURAÇÕES ===============

TOKEN = "7516174786:AAESsqNGZfOZupLTqDdOB0I_redMH6aEcHc"
PLANILHA_NOME = "CGLISTAS - GRUPOS"
CREDENCIAL_PATH = "credenciais.json"

INTERVALO_DISPARO = 60  # ⏱ tempo em segundos entre ciclos
LIMITAR_BOTOES = 5      # 🔢 quantidade de botões por ciclo

logging.basicConfig(level=logging.INFO)

# =============== CONEXÃO COM GOOGLE SHEETS ===============

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_B64")
    if not creds_b64:
        raise Exception("❌ Variável GOOGLE_CREDENTIALS_B64 não definida.")
    creds_json = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open(PLANILHA_NOME).sheet1
    return sheet

def carregar_grupos():
    sheet = conectar_sheets()
    registros = sheet.get_all_records()
    grupos = []
    for r in registros:
        grupos.append({
            "id": int(r["id"]),
            "nome": r["nome"],
            "fixado": r["fixado"] == "TRUE" or r["fixado"] is True
        })
    return grupos

def salvar_grupos(lista):
    sheet = conectar_sheets()
    sheet.clear()
    sheet.append_row(["id", "nome", "fixado"])
    for g in lista:
        fixado = "TRUE" if g.get("fixado") else ""
        sheet.append_row([g["id"], g["nome"], fixado])

def adicionar_grupo(grupo_id, nome):
    grupos = carregar_grupos()
    if not any(g["id"] == grupo_id for g in grupos):
        grupos.append({"id": grupo_id, "nome": nome})
        salvar_grupos(grupos)

def fixar_grupo(grupo_id):
    grupos = carregar_grupos()
    for g in grupos:
        if g["id"] == grupo_id:
            g["fixado"] = True
    salvar_grupos(grupos)

def desfixar_grupo(grupo_id):
    grupos = carregar_grupos()
    for g in grupos:
        if g["id"] == grupo_id:
            g["fixado"] = False
    salvar_grupos(grupos)

def obter_grupos_fixados():
    return [g for g in carregar_grupos() if g.get("fixado")]

# =============== COMANDOS ===============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    url = f"https://t.me/{bot_username}?startgroup&admin=post_messages+delete_messages+edit_messages+invite_users+pin_messages"
    teclado = [[InlineKeyboardButton("🟢 Adicionar Grupo", url=url)]]
    markup = InlineKeyboardMarkup(teclado)
    await update.message.reply_text(
        "😄 Bem-vindo!\n\nClique abaixo para adicionar o bot em um grupo:",
        reply_markup=markup
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Use: /admin fixar <id> ou /admin desfixar <id>")
        return
    acao, grupo_id = args[0], args[1]
    try:
        grupo_id = int(grupo_id)
    except:
        await update.message.reply_text("❌ ID inválido.")
        return
    if acao == "fixar":
        fixar_grupo(grupo_id)
        await update.message.reply_text(f"🌟 Grupo `{grupo_id}` fixado!", parse_mode="Markdown")
    elif acao == "desfixar":
        desfixar_grupo(grupo_id)
        await update.message.reply_text(f"🧹 Grupo `{grupo_id}` desfixado!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Ação inválida.")

# =============== ENTRADA EM GRUPO ===============

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat
    new_status = update.my_chat_member.new_chat_member.status
    user_id = update.my_chat_member.from_user.id
    if new_status in ["administrator", "member"]:
        await asyncio.sleep(2)
        bot_info = await context.bot.get_chat_member(chat.id, context.bot.id)
        if bot_info.status == "administrator":
            adicionar_grupo(chat.id, chat.title)
            await context.bot.send_message(chat.id, "✅ Esse grupo agora faz parte da lista de divulgação.")
            try:
                await context.bot.send_message(user_id, f"🟢 O grupo *{chat.title}* foi adicionado com sucesso.", parse_mode="Markdown")
            except:
                pass
        else:
            await context.bot.send_message(chat.id, "❌ O bot precisa ser admin. Saindo...")
            await context.bot.leave_chat(chat.id)
            try:
                await context.bot.send_message(user_id, f"⚠️ O bot saiu do grupo *{chat.title}*. Adicione como admin.", parse_mode="Markdown")
            except:
                pass

# =============== DIVULGAÇÃO AUTOMÁTICA ===============

async def divulgar(bot, limite_botoes=LIMITAR_BOTOES):
    grupos = carregar_grupos()
    if not grupos:
        logging.info("⚠️ Nenhum grupo disponível.")
        return

    fixados = obter_grupos_fixados()
    ultimo = grupos[-1]
    try:
        link_ultimo = await bot.create_chat_invite_link(ultimo["id"])
        destaque = f"👑 Último Grupo Adicionado:\n[{ultimo['nome']}]({link_ultimo.invite_link})"
    except:
        destaque = f"👑 Último Grupo Adicionado:\n{ultimo['nome']}"
    texto_base = f"🤖 Divulgação automática!\n\n{destaque}\n\n"

    for destino in grupos:
        try:
            teclado = []

            for g in fixados:
                if g["id"] != destino["id"]:
                    try:
                        convite = await bot.create_chat_invite_link(g["id"])
                        nome = f"🌟 {g['nome']}".ljust(20)
                        teclado.append([InlineKeyboardButton(nome, url=convite.invite_link)])
                    except:
                        pass

            comuns = [g for g in grupos if g["id"] != destino["id"] and not g.get("fixado")]
            promovidos = random.sample(comuns, min(len(comuns), limite_botoes))
            linha = []

            for g in promovidos:
                try:
                    convite = await bot.create_chat_invite_link(g["id"])
                    nome = g["nome"].center(18)
                    linha.append(InlineKeyboardButton(nome, url=convite.invite_link))
                    if len(linha) == 2:
                        teclado.append(linha)
                        linha = []
                except:
                    pass
            if linha:
                teclado.append(linha)

            url_add = f"https://t.me/{bot.username}?startgroup&admin=post_messages+delete_messages+edit_messages+invite_users+pin_messages"
            teclado.append([InlineKeyboardButton("🟢 Adicionar Grupo", url=url_add)])

            markup = InlineKeyboardMarkup(teclado)

            msg = await bot.send_message(
                chat_id=destino["id"],
                text=texto_base,
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

            try:
                await bot.pin_chat_message(chat_id=destino["id"], message_id=msg.message_id)
            except:
                logging.warning(f"⚠️ Não foi possível fixar no grupo {destino['nome']}")
        except Exception as e:
            logging.warning(f"Erro ao enviar para {destino['nome']}: {e}")

# =============== EXECUÇÃO DO BOT ===============

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    async def run_bot():
        async def disparos_automaticos():
            while True:
                logging.info("🚀 Iniciando ciclo de divulgação")
                try:
                    await divulgar(app.bot)
                except Exception as e:
                    logging.warning(f"❌ Erro durante disparo: {e}")
                await asyncio.sleep(INTERVALO_DISPARO)

        asyncio.create_task(disparos_automaticos())
        await app.run_polling()

    import nest_asyncio
    nest_asyncio.apply()

    asyncio.get_event_loop().run_until_complete(run_bot())

if __name__ == "__main__":
    main()
