import json
import random
import os
import pytz
import asyncio
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import subprocess
from datetime import datetime

# ----- Configurações Git -----
GIT_EMAIL = "cgcousingroup@gmail.com"
GIT_NOME = "cgcousingroup"
GIT_USER = "cgcousingroup"
GIT_REPO = "CGLISTAS"
GIT_TOKEN = "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i" # ⚠️ Use variável de ambiente na produção!
GIT_BRANCH = "master"  # ou "main"

# ----- Commit e Push automáticos -----
def enviar_git():
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"🔍 Verificando arquivos: {ARQUIVO_LISTA}, {ARQUIVO_GRUPOS}")
        if not os.path.exists(ARQUIVO_LISTA) or not os.path.exists(ARQUIVO_GRUPOS):
            print("⚠️ Arquivo(s) JSON não encontrados. Abortando commit.")
            return

        subprocess.run(["git", "config", "user.name", GIT_NOME], check=True)
        subprocess.run(["git", "config", "user.email", GIT_EMAIL], check=True)

        # Configura o remote usando o token no formato recomendado
        url_autenticada = f"git@github.com:{GIT_USER}/{GIT_REPO}.git"
        subprocess.run(["git", "remote", "set-url", "origin", url_autenticada], check=True)

        subprocess.run(["git", "add", ARQUIVO_LISTA, ARQUIVO_GRUPOS], check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", f"🔄 Atualização automática - {now}"], check=True)
        subprocess.run(["git", "push", "origin", GIT_BRANCH], check=True)

        print("✅ JSONs enviados ao GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar Git: {e}")


# ----- Configurações -----
TOKEN = "7878453101:AAE01jVm1Bk7BL55uEXL2soHRvzka5uS_h8"
ARQUIVO_GRUPOS = "grupos.json"
ARQUIVO_LISTA = "lista.json"
CODIGO_SECRETO = "123minhachave"
SENHA_ADMIN = "cgcsouingroup"
timezone = pytz.timezone("America/Sao_Paulo")

# ... O resto do seu código continua igual ...


# ----- Utilitários -----
def carregar_json(arquivo, padrao):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                return json.loads(conteudo) if conteudo else padrao
        except (json.JSONDecodeError, ValueError):
            return padrao
    return padrao

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

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

# ----- /adicionar_grupo -----
async def adicionar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nome = " ".join(context.args)
        lista = carregar_json(ARQUIVO_LISTA, [])
        if nome not in [g["link"] for g in lista if isinstance(g, dict)]:
            lista.append({"id": None, "nome": nome[:30], "link": nome})
            salvar_json(ARQUIVO_LISTA, lista)
            await update.message.reply_text("✅ Grupo adicionado à lista de divulgação.")
        else:
            await update.message.reply_text("⚠️ Esse grupo já está na lista.")
    else:
        await update.message.reply_text("❌ Use: /adicionar_grupo <link_do_grupo>")


# ----- Resposta ao botão "Adicionar Grupo" -----
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "adicionar_grupo":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?startgroup=true&admin=1"

        await query.edit_message_text(
            text=(
                "📌 Para adicionar o bot ao seu grupo:\n"
                "1️⃣ Clique no botão abaixo\n"
                "2️⃣ Escolha o grupo onde você é admin\n"
                "3️⃣ Marque as permissões recomendadas.\n\n"
                "⬇️ Toque aqui para adicionar:"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Adicionar ao Grupo", url=link)]
            ])
        )

# ----- /admin -----
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: /admin <id do grupo>")
        return

    try:
        gid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Envie apenas números.")
        return

    lista = carregar_json(ARQUIVO_LISTA, [])
    grupo = next((g for g in lista if g.get("id") == gid), None)

    if not grupo:
        await update.message.reply_text("❌ Grupo não encontrado no sistema.")
        return

    texto = (
        f"*Grupo:* {grupo['nome']}\n"
        f"🔗 {grupo['link']}\n"
        f"🆔 ID: {gid}\n"
        f"{'📌 Fixado' if grupo.get('fixado') else ''}"
    )
    botoes = [
        [
            InlineKeyboardButton("✏️ Nome", callback_data=f"editnome_{gid}"),
            InlineKeyboardButton("✏️ Link", callback_data=f"editlink_{gid}")
        ],
        [
            InlineKeyboardButton("📌 Fixar" if not grupo.get("fixado") else "📍 Desfixar", callback_data=f"togglefix_{gid}"),
            InlineKeyboardButton("🗑 Remover", callback_data=f"remover_{gid}")
        ]
    ]
    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(botoes), parse_mode="Markdown")


# ----- Callback dos botões -----
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Debug para ver o que está chegando
    print(f"Callback data recebido: {data}")

    lista = carregar_json(ARQUIVO_LISTA, [])

    # Verifica se o callback é um dos esperados
    if any(data.startswith(prefix) for prefix in ["editnome_", "editlink_", "togglefix_", "remover_"]):
        try:
            gid = int(data.split("_")[1])
        except ValueError:
            await query.edit_message_text("❌ ID inválido. Tente novamente.")
            return

        grupo = next((g for g in lista if g.get("id") == gid), None)
        if not grupo:
            await query.edit_message_text("❌ Grupo não encontrado.")
            return

        texto = (
            f"*Grupo:* {grupo['nome']}\n"
            f"🔗 {grupo['link']}\n"
            f"🆔 ID: {gid}\n"
            f"{'📌 Fixado' if grupo.get('fixado') else ''}"
        )
        botoes = [
            [
                InlineKeyboardButton("✏️ Nome", callback_data=f"editnome_{gid}"),
                InlineKeyboardButton("✏️ Link", callback_data=f"editlink_{gid}")
            ],
            [
                InlineKeyboardButton("📌 Fixar" if not grupo.get("fixado") else "📍 Desfixar", callback_data=f"togglefix_{gid}"),
                InlineKeyboardButton("🗑 Remover", callback_data=f"remover_{gid}")
            ]
        ]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(botoes), parse_mode="Markdown")

    else:
        # Se não for um callback reconhecido, apenas ignora silenciosamente ou responde com erro
        await query.edit_message_text("❌ Ação desconhecida. Tente novamente.")


# ----- Captura de edição -----
async def capturar_resposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "modo_edicao" not in context.user_data:
        return
    lista = carregar_json(ARQUIVO_LISTA, [])
    data = context.user_data.pop("modo_edicao")
    gid = int(data.split("_")[1])
    campo = "nome" if "editnome" in data else "link"
    for g in lista:
        if str(g.get("id")) == str(gid):
            g[campo] = update.message.text.strip()
            break
    salvar_json(ARQUIVO_LISTA, lista)
    await update.message.reply_text("✅ Editado com sucesso.")
    
    # Se estiver aguardando motivo de remoção
    if "modo_remocao" in context.user_data:
        gid = context.user_data.pop("modo_remocao")
        motivo = update.message.text.strip()
        lista = carregar_json(ARQUIVO_LISTA, [])
        grupo = next((g for g in lista if g.get("id") == gid), None)

        if grupo:
            try:
                dono = await update.get_bot().get_chat_administrators(gid)
                donos = [adm.user.id for adm in dono if adm.status == "creator"]
                if donos:
                    await update.get_bot().send_message(
                        chat_id=donos[0],
                        text=f"🚫 Seu grupo *{grupo['nome']}* foi removido da lista.\n📝 Motivo: {motivo}",
                        parse_mode="Markdown"
                    )
            except Exception as e:
                print(f"⚠️ Falha ao notificar dono: {e}")

            nova = [g for g in lista if g.get("id") != gid]
            salvar_json(ARQUIVO_LISTA, nova)

            try:
                await update.get_bot().leave_chat(gid)
            except:
                pass

        await update.message.reply_text("✅ Grupo removido e motivo enviado.")
        return


# ----- Comando /disparo -----
async def comando_disparo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] != CODIGO_SECRETO:
        await update.message.reply_text("❌ Código inválido.")
        return
    await update.message.reply_text("🚀 Disparando agora...")
    await disparar_listas(context.bot)
    enviar_git()

# ----- Disparo com botões -----
async def disparar_listas(bot):
    grupos = carregar_json(ARQUIVO_GRUPOS, [])
    lista = carregar_json(ARQUIVO_LISTA, [])
    if not lista:
        print("⚠️ Lista vazia.")
        return
    lista_ordenada = sorted(lista, key=lambda g: not g.get("fixado", False))
    amostra = random.sample(lista_ordenada, min(30, len(lista_ordenada)))

    for grupo_id in grupos:
        botoes = [[InlineKeyboardButton(g["nome"][:30], url=g["link"])] for g in amostra]
        markup = InlineKeyboardMarkup(botoes)
        try:
            await bot.send_message(
                chat_id=grupo_id,
                text="📢 *Grupos Parceiros:*",
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception as e:
            print(f"❌ Erro: {e}")

async def disparar_listas_job(context: ContextTypes.DEFAULT_TYPE):
    await disparar_listas(context.bot)
    enviar_git()  # Adicionado aqui!

# ----- Quando o bot é adicionado -----
async def bot_adicionado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = update.my_chat_member
    if not chat_member:
        return

    chat = chat_member.chat
    user = chat_member.from_user  # quem adicionou/mudou status do bot

    novo_status = chat_member.new_chat_member.status
    antigo_status = chat_member.old_chat_member.status

    # Só age quando o bot entra (de left/kicked para member/administrator)
    if novo_status in ["member", "administrator"] and antigo_status in ["left", "kicked"]:
        await asyncio.sleep(3)  # espera 3 segundos antes de checar

        # Recheca status atualizado do bot no grupo
        membro = await context.bot.get_chat_member(chat.id, context.bot.id)
        if membro.status != "administrator":
            # Bot é membro comum — sai e avisa quem adicionou no privado
            try:
                await context.bot.leave_chat(chat.id)
            except Exception as e:
                print(f"⚠️ Erro ao sair do grupo: {e}")

            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=(
                        f"⚠️ Fui adicionado ao grupo *{chat.title}* como membro comum e saí.\n"
                        "Para funcionar, preciso ser administrador. Por favor, promova-me."
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"⚠️ Falha ao enviar mensagem para quem adicionou: {e}")
            return

        # Bot é admin — registra grupo, avisa grupo e quem adicionou no privado
        grupos = carregar_json(ARQUIVO_GRUPOS, [])
        if chat.id not in grupos:
            grupos.append(chat.id)
            salvar_json(ARQUIVO_GRUPOS, grupos)

        try:
            convite = await context.bot.export_chat_invite_link(chat.id)
        except Exception as e:
            convite = "Link indisponível"
            print(f"❌ Erro ao obter link de convite: {e}")

        lista = carregar_json(ARQUIVO_LISTA, [])
        ja_existe = any(g.get("id") == chat.id for g in lista)
        if not ja_existe:
            lista.append({
                "id": chat.id,
                "nome": chat.title,
                "link": convite,
                "fixado": False
            })
            salvar_json(ARQUIVO_LISTA, lista)
            print(f"✅ Grupo registrado: {chat.title} ({chat.id})")

        # Avise no grupo
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text="✅ Fui promovido a administrador e estou pronto para funcionar!"
            )
        except Exception as e:
            print(f"⚠️ Falha ao enviar mensagem no grupo: {e}")

        # Avise quem adicionou no privado
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"✅ Obrigado por me adicionar e promover no grupo *{chat.title}*.\n"
                    "Estou pronto para ajudar na divulgação."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ Falha ao enviar mensagem para quem adicionou: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adicionar_grupo", adicionar_grupo))
    app.add_handler(CommandHandler("disparo", comando_disparo))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(ChatMemberHandler(bot_adicionado, ChatMemberHandler.MY_CHAT_MEMBER))

    # Primeiro, handlers com pattern específico
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^adicionar_grupo$"))

    # Depois, o admin_callback que trata os botões do painel
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(editnome_|editlink_|togglefix_|remover_)"))

    # Captura de mensagens privadas (respostas de edição, etc.)
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, capturar_resposta))

    # Configura o timezone corretamente no agendador
    app.job_queue.scheduler.configure(timezone=timezone)
    app.job_queue.run_repeating(disparar_listas_job, interval=10, first=0)

    print("🚀 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
