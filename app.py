import os
import subprocess
from datetime import datetime
import logging
from types import SimpleNamespace
import asyncio
import json
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatMemberHandler,
    ContextTypes,
)
from pathlib import Path

# ================= CONFIGURAÇÕES =================

TOKEN = "7516174786:AAESsqNGZfOZupLTqDdOB0I_redMH6aEcHc"
JSON_PATH = "grupos.json"

GIT_EMAIL = "cgcousingroup@gmail.com"
GIT_NOME = "cgcousingroup"
GIT_USER = "cgcousingroup"
GIT_REPO = "CGLISTAS"
GIT_BRANCH = "master"

logging.basicConfig(level=logging.INFO)

# ================= FUNÇÃO DE COMMIT AUTOMÁTICO =================

def enviar_git():
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not os.path.exists(JSON_PATH):
            logging.warning("⚠️ grupos.json não encontrado. Abortando envio.")
            return

        subprocess.run(["git", "config", "user.name", GIT_NOME], check=True)
        subprocess.run(["git", "config", "user.email", GIT_EMAIL], check=True)

        url_autenticada = f"git@github.com:{GIT_USER}/{GIT_REPO}.git"
        subprocess.run(["git", "remote", "set-url", "origin", url_autenticada], check=True)

        subprocess.run(["git", "add", JSON_PATH], check=True)
        subprocess.run(["git", "commit", "-m", f"🔄 Atualização automática - {now}"], check=True)

        try:
            subprocess.run(["git", "pull", "--rebase", "origin", GIT_BRANCH], check=True)
        except subprocess.CalledProcessError as e:
            logging.warning(f"⚠️ Pull falhou, mas forçando push mesmo assim: {e}")

        subprocess.run(["git", "push", "--force", "origin", GIT_BRANCH], check=True)
        logging.info("✅ grupos.json enviado ao GitHub com push forçado.")
    except subprocess.CalledProcessError as e:
        logging.warning(f"❌ Erro ao executar Git: {e}")

# ================= UTILITÁRIOS =================

def carregar_grupos():
    if not Path(JSON_PATH).exists():
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_grupos(lista):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(lista, f, indent=2, ensure_ascii=False)

def adicionar_grupo(grupo_id, nome):
    grupos = carregar_grupos()
    if not any(g["id"] == grupo_id for g in grupos):
        grupos.append({"id": grupo_id, "nome": nome})
        salvar_grupos(grupos)

# ================= COMANDO /START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    url_adicionar = f"https://t.me/{bot_username}?startgroup&admin=post_messages+delete_messages+edit_messages+invite_users+pin_messages"
    teclado = [[InlineKeyboardButton("🟢 Adicionar Grupo", url=url_adicionar)]]
    markup = InlineKeyboardMarkup(teclado)
    await update.message.reply_text(
        "😄 Bem-vindo ao Bot de Parcerias!\n\n"
        "🔗 Clique no botão abaixo para adicionar o bot em seu grupo e começar a divulgar.",
        reply_markup=markup
    )

# ================= ENTRADA EM GRUPO =================

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat
    new_status = update.my_chat_member.new_chat_member.status
    user_id = update.my_chat_member.from_user.id

    if new_status in ["administrator", "member"]:
        await asyncio.sleep(2)
        bot_info = await context.bot.get_chat_member(chat.id, context.bot.id)

        if bot_info.status == "administrator":
            adicionar_grupo(chat.id, chat.title)

            # ✅ Sincroniza após adicionar
            salvar_grupos(carregar_grupos())
            enviar_git()

            await context.bot.send_message(chat.id, "✅ Esse grupo agora faz parte da lista de divulgação.")
            try:
                await context.bot.send_message(user_id, f"🟢 O grupo *{chat.title}* foi adicionado com sucesso à lista.", parse_mode="Markdown")
            except:
                pass
        else:
            await context.bot.send_message(chat.id, "❌ O bot precisa ser administrador. Saindo...")
            await context.bot.leave_chat(chat.id)
            try:
                await context.bot.send_message(user_id, f"⚠️ O bot saiu do grupo *{chat.title}*. Adicione como admin.", parse_mode="Markdown")
            except:
                pass

# ================= DIVULGAÇÃO AUTOMÁTICA =================

async def divulgar(bot, limite_botoes=2):
    grupos = carregar_grupos()
    if not grupos:
        logging.info("⚠️ Nenhum grupo disponível para divulgação.")
        return

    grupos_embaralhados = random.sample(grupos, len(grupos))
    promovidos = grupos_embaralhados[:limite_botoes]
    botoes = []

    for g in promovidos:
        try:
            convite = await bot.create_chat_invite_link(g["id"])
            url_convite = convite.invite_link
            botoes.append([InlineKeyboardButton(f"{g['nome']}", url=url_convite)])
        except Exception as e:
            logging.warning(f"Erro ao gerar link para {g['nome']}: {e}")

    markup = InlineKeyboardMarkup(botoes)

    ultimo_grupo = grupos[-1]

    try:
        convite_ultimo = await bot.create_chat_invite_link(ultimo_grupo["id"])
        url_ultimo = convite_ultimo.invite_link
        destaque = f"👑 Último Grupo Adicionado:\n[{ultimo_grupo['nome']}]({url_ultimo})"
    except Exception as e:
        logging.warning(f"Erro ao gerar link do último grupo: {e}")
        destaque = f"👑 Último Grupo Adicionado:\n{ultimo_grupo['nome']} (link indisponível)"

    texto = (
        "🤖 Divulgação gratuita e automática!\n\n"
        f"{destaque}\n\n"
    )

    for grupo in grupos:
        try:
            await bot.send_message(
                chat_id=grupo["id"],
                text=texto,
                reply_markup=markup,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            salvar_grupos(grupos)
            enviar_git()
            await asyncio.sleep(1)
        except Exception as e:
            logging.warning(f"Erro ao enviar para {grupo['nome']}: {e}")

# ================= INICIAR BOT =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    async def run_bot():
        async def disparos_automaticos():
            while True:
                logging.info("🚀 Disparo automático iniciado")
                try:
                    await divulgar(app.bot, limite_botoes=2)
                except Exception as e:
                    logging.warning(f"❌ Erro durante disparo: {e}")
                try:
                    enviar_git()
                except Exception as e:
                    logging.warning(f"⚠️ Falha ao atualizar Git após ciclo: {e}")
                await asyncio.sleep(10)

        asyncio.create_task(disparos_automaticos())
        await app.run_polling()

    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
