import sys
print("Python version:", sys.version)
print("Starting bot...")
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
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN bulunamadi!")

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
   await update.message.reply_text(
       "Kira Takip Botuna Hos Geldiniz!\n\nNe yapmak istersiniz?",
       reply_markup=InlineKeyboardMarkup(keyboard)
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
   await query.edit_message_text(
       "Kira Takip Botu - Ana Menu",
       reply_markup=InlineKeyboardMarkup(keyboard)
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
       await update.message.reply_text("Odeme gunu kac? (1-31):")
       return TARIH
   except ValueError:
       await update.message.reply_text("Gecerli bir sayi yazin (ornek: 5000)")
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
           "Kiraci eklendi!\nAd: " + kiraci["ad"] + " " + kiraci["soyad"] + "\nDaire: " + kiraci["daire"] + "\nKira: " + str(int(kiraci["kira"])) + " TL\nOdeme gunu: " + str(gun),
           reply_markup=InlineKeyboardMarkup(keyboard)
       )
       return ConversationHandler.END
   except ValueError:
       await update.message.reply_text("1-31 arasi bir sayi yazin:")
       return TARIH

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
   await update.message.reply_text("Iptal edildi.")
   return ConversationHandler.END

async def listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   data = veri_yukle()
   kiracılar = data["kiracılar"]
   if not kiracılar:
       keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
       await query.edit_message_text("Henuz kiraci yok.", reply_markup=InlineKeyboardMarkup(keyboard))
       return
   bugun = datetime.now()
   ay_key = bugun.strftime("%Y-%m")
   mesaj = "Kiraci Listesi\n\n"
   for k in kiracılar:
       odendi = ay_key in k.get("odendi_aylar", [])
       durum = "Odendi" if odendi else "Odenmedi"
       mesaj = mesaj + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"] + "\n" + str(int(k["kira"])) + " TL | " + str(k["odeme_gunu"]) + ". gun | " + durum + "\n\n"
   keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
   await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))

async def odeme_listesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   data = veri_yukle()
   kiracılar = data["kiracılar"]
   if not kiracılar:
       keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
       await query.edit_message_text("Henuz kiraci yok.", reply_markup=InlineKeyboardMarkup(keyboard))
       return
   ay_key = datetime.now().strftime("%Y-%m")
   keyboard = []
   for k in kiracılar:
       odendi = ay_key in k.get("odendi_aylar", [])
       if odendi:
           etiket = "[OK] " + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"]
       else:
           etiket = "[BEKLIYOR] " + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"]
       keyboard.append([InlineKeyboardButton(etiket, callback_data="toggle_" + k["id"])])
   keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
   await query.edit_message_text("Odeme Durumu - Tiklayarak degistirin:", reply_markup=InlineKeyboardMarkup(keyboard))

async def odeme_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
   query = update.callback_query
   await query.answer()
   kiraci_id = query.data.replace("toggle_", "")
   data = veri_yukle()
   ay_key = datetime.now().strftime("%Y-%m")
   mesaj = ""
   for k in data["kiracılar"]:
       if k["id"] == kiraci_id:
           if ay_key in k.get("odendi_aylar", []):
               k["odendi_aylar"].remove(ay_key)
               mesaj = k["ad"] + " " + k["soyad"] + " - geri alindi"
           else:
               k.setdefault("odendi_aylar", []).append(ay_key)
               mesaj = k["ad"] + " " + k["soyad"] + " - odendi isaretlendi"
           break
   veri_kaydet(data)
   keyboard = []
   for k in data["kiracılar"]:
       odendi = ay_key in k.get("odendi_aylar", [])
       if odendi:
           etiket = "[OK] " + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"]
       else:
           etiket = "[BEKLIYOR] " + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"]
       keyboard.append([InlineKeyboardButton(etiket, callback_data="toggle_" + k["id"])])
   keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
   await query.edit_message_text("Odeme Durumu\n" + mesaj + "\n\nTiklayarak degistirin:", reply_markup=InlineKeyboardMarkup(keyboard))
