import os
import json
import logging
from datetime import datetime
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
       [InlineKeyboardButton("Kiraci Ekle", callback_data="kiraci_ekle")],
       [InlineKeyboardButton("Kiracilari Listele", callback_data="listele")],
       [InlineKeyboardButton("Odeme Isaretle", callback_data="odeme")],
       [InlineKeyboardButton("Durum Raporu", callback_data="rapor")],
   ]
   reply_markup = InlineKeyboardMarkup(keyboard)
   await update.message.reply_text(
       "*Kira Takip Botuna Hos Geldiniz!*\n\nNe yapmak istersiniz?",
       reply_markup=reply_markup,
       parse_mode="Markdown"
   )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   keyboard = [
       [InlineKeyboardButton("Kiraci Ekle", callback_data="kiraci_ekle")],
       [InlineKeyboardButton("Kiracilari Listele", callback_data="listele")],
       [InlineKeyboardButton("Odeme Isaretle", callback_data="odeme")],
       [InlineKeyboardButton("Durum Raporu", callback_data="rapor")],
   ]
   reply_markup = InlineKeyboardMarkup(keyboard)
   await query.edit_message_text(
       "*Kira Takip Botu*\n\nNe yapmak istersiniz?",
       reply_markup=reply_markup,
       parse_mode="Markdown"
   )

async def kiraci_ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   await query.edit_message_text("Kiraciinin adini yazin:")
   return AD

async def ad_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
   context.user_data["yeni_kiraci"] = {"ad": update.message.text}
   await update.message.reply_text("Kiraciinin soyadini yazin:")
   return SOYAD

async def soyad_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
   context.user_data["yeni_kiraci"]["soyad"] = update.message.text
   await update.message.reply_text("Daire numarasini yazin (ornek: 3A):")
   return DAIRE

async def daire_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
   context.user_data["yeni_kiraci"]["daire"] = update.message.text
   await update.message.reply_text("Aylik kira tutarini yazin (ornek: 5000):")
   return KIRA

async def kira_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
   try:
       tutar = float(update.message.text.replace(",", "."))
       context.user_data["yeni_kiraci"]["kira"] = tutar
       await update.message.reply_text("Kira odeme gunu kac? (1-31 arasi bir sayi yazin):")
       return TARIH
   except ValueError:
       await update.message.reply_text("Lutfen gecerli bir sayi yazin (ornek: 5000)")
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
       keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
       await update.message.reply_text(
           f"Kiraci basariyla eklendi!\n\nAd: {kiraci['ad']} {kiraci['soyad']}\nDaire: {kiraci['daire']}\nKira: {kiraci['kira']:,.0f} TL\nOdeme gunu: Her ayin {gun}. gunu",
           reply_markup=InlineKeyboardMarkup(keyboard)
       )
       return ConversationHandler.END
   except ValueError:
       await update.message.reply_text("Lutfen 1-31 arasi bir sayi yazin:")
       return TARIH

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
   await update.message.reply_text("Islem iptal edildi.")
   return ConversationHandler.END

async def listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   data = veri_yukle()
   kiracılar = data["kiracılar"]
   if not kiracılar:
       keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
       await query.edit_message_text("Henuz kiraci eklenmemis.", reply_markup=InlineKeyboardMarkup(keyboard))
       return
   mesaj = "Kiraci Listesi\n\n"
   bugun = datetime.now()
   for k in kiracılar:
       ay_key = bugun.strftime("%Y-%m")
       odendi = ay_key in k.get("odendi_aylar", [])
       durum = "Odendi" if odendi else "Odenmedi"
       mesaj += f"{k['ad']} {k['soyad']} - Daire {k['daire']}\n"
       mesaj += f"  {k['kira']:,.0f} TL | {k['odeme_gunu']}. gun | {durum}\n\n"
   keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
   await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))

async def odeme_listesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   data = veri_yukle()
   kiracılar = data["kiracılar"]
   if not kiracılar:
       keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
       await query.edit_message_text("Henuz kiraci eklenmemis.", reply_markup=InlineKeyboardMarkup(keyboard))
       return
   bugun = datetime.now()
   ay_key = bugun.strftime("%Y-%m")
   keyboard = []
   for k in kiracılar:
       odendi = ay_key in k.get("odendi_aylar", [])
       etiket = f"{'[ODENDI]' if odendi else '[BEKLIYOR]'} {k['ad']} {k['soyad']} - Daire {k['daire']}"
       keyboard.append([InlineKeyboardButton(etiket, callback_data=f"toggle_{k['id']}")])
   keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
   await query.edit_message_text(
       "Odeme Durumu - Tiklayarak degistirin:",
       reply_markup=InlineKeyboardMarkup(keyboard)
   )

async def odeme_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   kiraci_id = query.data.replace("toggle_", "")
   data = veri_yukle()
   bugun = datetime.now()
   ay_key = bugun.strftime("%Y-%m")
   mesaj = ""
   for k in data["kiracılar"]:
       if k["id"] == kiraci_id:
           if ay_key in k.get("odendi_aylar", []):
               k["odendi_aylar"].remove(ay_key)
               mesaj = f"{k['ad']} {k['soyad']} - odeme geri alindi"
           else:
               k.setdefault("odendi_aylar", []).append(ay_key)
               mesaj = f"{k['ad']} {k['soyad']} - odeme isaretlendi"
           break
   veri_kaydet(data)
   kiracılar = data["kiracılar"]
   keyboard = []
   for k in kiracılar:
       odendi = ay_key in k.get("odendi_aylar", [])
       etiket = f"{'[ODENDI]' if odendi else '[BEKLIYOR]'} {k['ad']} {k['soyad']} - Daire {k['daire']}"
       keyboard.append([InlineKeyboardButton(etiket, callback_data=f"toggle_{k['id']}")])
   keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
   await query.edit_message_text(
       f"Odeme Durumu\n{mesaj}\n\nTiklayarak degistirin:",
       reply_markup=InlineKeyboardMarkup(keyboard)
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
       f"{bugun.strftime('%B %Y')} Raporu\n\n"
       f"Toplam kiraci: {toplam}\n"
       f"Odeme yapan: {odenenler}\n"
       f"Odeme yapmayan: {odenmeyenler}\n\n"
       f"Beklenen kira: {toplam_kira:,.0f} TL\n"
       f"Toplanan: {toplanan:,.0f} TL\n"
       f"Bekleyen: {toplam_kira - toplanan:,.0f} TL"
   )
   keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
   await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))

async def hatirlatma_gonder(context: ContextTypes.DEFAULT_TYPE):
   data = veri_yukle()
   bugun = datetime.now()
   ay_key = bugun.strftime("%Y-%m")
   chat_id = context.job.data
   for k in data["kiracılar"]:
       odeme_gunu = k["odeme_gunu"]
       odendi = ay_key in k.get("odendi_aylar", [])
       kalan_gun = odeme_gunu - bugun.day
       if not odendi and kalan_gun in [3, 1, 0]:
           if kalan_gun == 0:
               mesaj = f"Bugun odeme gunu!\n{k['ad']} {k['soyad']} (Daire {k['daire']})\n{k['kira']:,.0f} TL"
           else:
               mesaj = f"{kalan_gun} gun sonra odeme!\n{k['ad']} {k['soyad']} (Daire {k['daire']})\n{k['kira']:,.0f} TL"
           await context.bot.send_message(chat_id=chat_id, text=mesaj)

async def hatirlatma_ayarla(update: Update, context: ContextTypes.DEFAULT_TYPE):
   chat_id = update.effective_chat.id
   context.job_queue.run_daily(
       hatirlatma_gonder,
       time=datetime.strptime("09:00", "%H:%M").time(),
       data=chat_id,
       name=str(chat_id)
   )
   await update.message.reply_text("Gunluk hatirlatmalar acildi! Her gun 09:00'da kontrol edilecek.")

def main():
   app = Application.builder().token(TOKEN).build()
   conv_handler = ConversationHandler(
       entry_points=[CallbackQueryHandler(kiraci_ekle_baslat, pattern="kiraci_ekle")],
       states={
           AD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ad_al)],
           SOYAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, soyad_al)],
           DAIRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, daire_al)],
           KIRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, kira_al)],
           TARIH: [MessageHandler(filters.TEXT & ~filters.COMMAND, tarih_al)],
       },
       fallbacks=[CommandHandler("iptal", iptal)],
   )
   app.add_handler(CommandHandler("start", start))
   app.add_handler(CommandHandler("hatirlatma", hatirlatma_ayarla))
   app.add_handler(conv_handler)
   app.add_handler(CallbackQueryHandler(menu, pattern="ana_menu"))
   app.add_handler(CallbackQueryHandler(listele, pattern="listele"))
   app.add_handler(CallbackQueryHandler(odeme_listesi, pattern="odeme"))
   app.add_handler(CallbackQueryHandler(rapor, pattern="rapor"))
   app.add_handler(CallbackQueryHandler(odeme_toggle, pattern="toggle_"))
   print("Bot baslatildi...")
   app.run_polling()

if __name__ == "__main__":
   main()
