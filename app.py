import json
import random
import os
import pytz
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
)

# ----- Configurações -----
TOKEN = "7878453101:AAE01jVm1Bk7BL55uEXL2soHRvzka5uS_h8"
ARQUIVO_GRUPOS = "grupos.json"
ARQUIVO_LISTA = "lista.json"
INTERVALO_HORAS = 6
timezone = pytz.timezone("America/Sao_Paulo")

# ----- Utilitários -----
def carregar_json(arquivo, padrao):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r") as f:
                conteudo = f.read().strip()
                return json.loads(conteudo) if conteudo else padrao
        except (json.JSONDecodeError, ValueError):
            return padrao
    return padrao

def salvar_json(arquivo, dados):
    with open(arquivo, "w") as f:
        json.dump(dados, f, indent=2)

# ----- /start -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = len(carregar_json(ARQUIVO_GRUPOS, []))
    texto = (
        "👋 Olá! Seja bem-vindo ao *Bot de Parcerias!*\n\n"
        f"📌 Temos *{total}* grupos registrados.\n"
        "🔗 Este bot divulga links automaticamente entre grupos.\n"
        "⏱️ Requisitos: manter a lista visível por 24h.\n\n"
        "👇 Toque no botão abaixo para começar:"
    )
    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Adicionar Grupo", callback_data="adicionar_grupo")]
    ])
    if update.message:
        await update.message.reply_text(texto, reply_markup=teclado, parse_mode="Markdown")

# ----- Botão “Adicionar Grupo” -----
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?startgroup=true&admin=1"

    await query.message.reply_text(
        "📌 Para adicionar o bot ao grupo:\n"
        "1️⃣ Clique no botão abaixo\n"
        "2️⃣ Escolha um grupo onde você é admin\n"
        "3️⃣ O Telegram abrirá a tela para marcar as permissões\n\n"
        "⚠️ Marque permissões como:\n"
        "• Enviar mensagens\n• Apagar mensagens\n• Fixar mensagens\n• Convidar por link\n\n"
        "⬇️ Toque aqui:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Selecionar Grupo", url=link)]
        ])
    )

# ----- Quando o bot é adicionado -----
async def bot_adicionado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = update.my_chat_member
    if not chat_member:
        return

    chat = chat_member.chat
    user = chat_member.from_user
    novo = chat_member.new_chat_member.status
    antigo = chat_member.old_chat_member.status
    bot_username = (await context.bot.get_me()).username

    print(f"🧪 Novo status do bot no grupo {chat.title}: {novo}")

    if novo in ["member", "administrator"] and antigo in ["left", "kicked"]:
        if novo != "administrator":
            await asyncio.sleep(4)
            membro = await context.bot.get_chat_member(chat.id, context.bot.id)
            if membro.status != "administrator":
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=(
                            f"⚠️ O bot *@{bot_username}* foi adicionado ao grupo *{chat.title}*, "
                            "mas sem permissões de administrador.\n\n"
                            "🚫 Ele sairá do grupo agora. Por favor, adicione-o novamente como *administrador* "
                            "para funcionar corretamente."
                        ),
                        parse_mode="Markdown"
                    )
                except:
                    pass

                try:
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text="⚠️ Este bot só funciona como administrador. Saindo do grupo."
                    )
                except:
                    pass

                await context.bot.leave_chat(chat.id)
                return

        grupos = carregar_json(ARQUIVO_GRUPOS, [])
        if chat.id not in grupos:
            grupos.append(chat.id)
            salvar_json(ARQUIVO_GRUPOS, grupos)

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"✅ *{bot_username}* foi adicionado ao grupo como administrador!\n\n"
                    "🔧 Permissões recomendadas:\n"
                    "• Enviar mensagens\n• Apagar mensagens\n• Fixar mensagens\n• Convidar via link"
                ),
                parse_mode="Markdown"
            )
        except:
            pass

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"✅ O bot foi adicionado ao grupo *{chat.title}* e está funcionando corretamente!",
                parse_mode="Markdown"
            )
        except:
            pass

# ----- /adicionar_grupo -----
async def adicionar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nome = " ".join(context.args)
        lista = carregar_json(ARQUIVO_LISTA, [])
        if nome not in lista:
            lista.append(nome)
            salvar_json(ARQUIVO_LISTA, lista)
            await update.message.reply_text("✅ Grupo adicionado à lista de divulgação.")
        else:
            await update.message.reply_text("⚠️ Esse grupo já está na lista.")
    else:
        await update.message.reply_text("❌ Use: /adicionar_grupo <nome_link>")

# ----- Envio automático de listas -----
async def disparar_listas(bot):
    grupos = carregar_json(ARQUIVO_GRUPOS, [])
    lista = carregar_json(ARQUIVO_LISTA, [])
    if not lista:
        return

    lista_base = random.sample(lista, min(30, len(lista)))
    for grupo_id in grupos:
        lista_embaralhada = random.sample(lista_base, len(lista_base))
        mensagem = "📢 *Links de Grupos* 📢\n\n" + "\n".join(f"🔗 {g}" for g in lista_embaralhada)
        try:
            await bot.send_message(chat_id=grupo_id, text=mensagem, parse_mode="Markdown")
        except Exception as e:
            print(f"Erro ao enviar para {grupo_id}: {e}")

async def disparar_listas_job(context: ContextTypes.DEFAULT_TYPE):
    await disparar_listas(context.bot)

# ----- Inicialização -----
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatMemberHandler(bot_adicionado, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("adicionar_grupo", adicionar_grupo))

    app.job_queue.scheduler.configure(timezone=timezone)
    app.job_queue.run_repeating(disparar_listas_job, interval=INTERVALO_HORAS * 3600, first=10)

    print("🚀 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
