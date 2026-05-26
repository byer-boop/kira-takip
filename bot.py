import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = "kiraci_data.json"

AD, SOYAD, DAIRE, KIRA, TARIH = range(5)

def veri_yukle():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"kiracılar": []}

def veri_kaydet(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Kiracı Ekle", callback_data="kiraci_ekle")],
        [InlineKeyboardButton("📋 Kiracıları Listele", callback_data="listele")],
        [InlineKeyboardButton("✅ Ödeme İşaretle", callback_data="odeme")],
        [InlineKeyboardButton("📊 Durum Raporu", callback_data="rapor")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏠 *Kira Takip Botuna Hoş Geldiniz!*\n\nNe yapmak istersiniz?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ Kiracı Ekle", callback_data="kiraci_ekle")],
        [InlineKeyboardButton("📋 Kiracıları Listele", callback_data="listele")],
        [InlineKeyboardButton("✅ Ödeme İşaretle", callback_data="odeme")],
        [InlineKeyboardButton("📊 Durum Raporu", callback_data="rapor")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🏠 *Kira Takip Botu*\n\nNe yapmak istersiniz?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def kiraci_ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👤 Kiracının *adını* yazın:", parse_mode="Markdown")
    return AD

async def ad_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["yeni_kiraci"] = {"ad": update.message.text}
    await update.message.reply_text("👤 Kiracının *soyadını* yazın:", parse_mode="Markdown")
    return SOYAD

async def soyad_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["yeni_kiraci"]["soyad"] = update.message.text
    await update.message.reply_text("🏠 *Daire numarasını* yazın (örn: 3A):", parse_mode="Markdown")
    return DAIRE

async def daire_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["yeni_kiraci"]["daire"] = update.message.text
    await update.message.reply_text("💰 Aylık *kira tutarını* yazın (örn: 5000):", parse_mode="Markdown")
    return KIRA

async def kira_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tutar = float(update.message.text.replace(",", "."))
        context.user_data["yeni_kiraci"]["kira"] = tutar
        await update.message.reply_text(
            "📅 Kira *ödeme günü* kaç? (1-31 arası bir sayı yazın):",
            parse_mode="Markdown"
        )
        return TARIH
    except ValueError:
        await update.message.reply_text("❌ Lütfen geçerli bir sayı yazın (örn: 5000)")
        return KIRA

async def tarih_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gun = int(update.message.text)
        if not 1 <= gun <= 31:
            raise ValueError
        kiraci = context.user_data["yeni_kiraci"]
        kiraci["odeme_gunu"] = gun
        kiraci["odendi_aylar"] = []
        kiraci["id"] = datetime.now().strftime("%Y%m%d%H%M%S")
        data = veri_yukle()
        data["kiracılar"].append(kiraci)
        veri_kaydet(data)
        keyboard = [[InlineKeyboardButton("🏠 Ana Menü", callback_data="ana_menu")]]
        await update.message.reply_text(
            f"✅ *Kiracı başarıyla eklendi!*\n\n"
            f"👤 {kiraci['ad']} {kiraci['soyad']}\n"
            f"🏠 Daire: {kiraci['daire']}\n"
            f"💰 Kira: {kiraci['kira']:,.0f} ₺\n"
            f"📅 Ödeme günü: Her ayın {gun}. günü",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Lütfen 1-31 arası bir sayı yazın:")
        return TARIH

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ İşlem iptal edildi.")
    return ConversationHandler.END

async def listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    if not kiracılar:
        keyboard = [[InlineKeyboardButton("🏠 Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text("📋 Henüz kiracı eklenmemiş.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    mesaj = "📋 *Kiracı Listesi*\n\n"
    bugun = datetime.now()
    for k in kiracılar:
        ay_key = bugun.strftime("%Y-%m")
        odendi = ay_key in k.get("odendi_aylar", [])
        durum = "✅ Ödendi" if odendi else "❌ Ödenmedi"
        mesaj += f"👤 {k['ad']} {k['soyad']} - Daire {k['daire']}\n"
        mesaj += f"   💰 {k['kira']:,.0f} ₺ | 📅 {k['odeme_gunu']}. gün | {durum}\n\n"
    keyboard = [[InlineKeyboardButton("🏠 Ana Menü", callback_data="ana_menu")]]
    await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def odeme_listesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    if not kiracılar:
        keyboard = [[InlineKeyboardButton("🏠 Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text("📋 Henüz kiracı eklenmemiş.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    bugun = datetime.now()
    ay_key = bugun.strftime("%Y-%m")
    keyboard = []
    for k in kiracılar:
        odendi = ay_key in k.get("odendi_aylar", [])
        etiket = f"{'✅' if odendi else '❌'} {k['ad']} {k['soyad']} - Daire {k['daire']}"
        keyboard.append([InlineKeyboardButton(etiket, callback_data=f"toggle_{k['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 Ana Menü", callback_data="ana_menu")])
    await query.edit_message_text(
        "✅ *Ödeme Durumu*\nBir kiracıya tıklayarak ödeme durumunu değiştirin:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def odeme_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kiraci_id = query.data.replace("toggle_", "")
    data = veri_yukle()
    bugun = datetime.now()
    ay_key = bugun.strftime("%Y-%m")
    for k in data["kiracılar"]:
        if k["id"] == kiraci_id:
            if ay_key in k.get("odendi_aylar", []):
                k["odendi_aylar"].remove(ay_key)
                mesaj = f"❌ {k['ad']} {k['soyad']} - ödeme geri alındı"
            else:
                k.setdefault("odendi_aylar", []).append(ay_key)
                mesaj = f"✅ {k['ad']} {k['soyad']} - ödeme işaretlendi"
            break
    veri_kaydet(data)
    kiracılar = data["kiracılar"]
    keyboard = []
    for k in kiracılar:
        odendi = ay_key in k.get("odendi_aylar", [])
        etiket = f"{'✅' if odendi else '❌'} {k['ad']} {k['soyad']} - Daire {k['daire']}"
        keyboard.append([InlineKeyboardButton(etiket, callback_data=f"toggle_{k['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 Ana Menü", callback_data="ana_menu")])
    await query.edit_message_text(
        f"✅ *Ödeme Durumu*\n_{mesaj}_\n\nBir kiracıya tıklayarak ödeme durumunu değiştirin:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    bugun = datetime.now()
    ay_key = bugun.strftime("%Y-%m")
    toplam = len(kiracılar)
    odenenler = sum(1 for k in kiracılar if ay_key in k.get("odendi_aylar", []))
    odenmeyenler = toplam - odenenler
    toplam_kira = sum(k["kira"] for k in kiracılar)
    toplanan = sum(k["kira"] for k in kiracılar if ay_key in k.get("odendi_aylar", []))
    mesaj = (
        f"📊 *{bugun.strftime('%B %Y')} Raporu*\n\n"
        f"👥 
