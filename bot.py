import sys
import traceback
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
BORC_FILE = "borc_data.json"

AD, SOYAD, DAIRE, KIRA, TARIH, DEPOZITO = range(6)
BORC_AD, BORC_MIKTAR, BORC_TARIH = range(6, 9)
ZAM_ID, ZAM_MIKTAR = range(9, 11)
ISIM_ID, ISIM_YENI = range(11, 13)
KISMI_ID, KISMI_MIKTAR = range(13, 15)

def veri_yukle():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"kiracılar": []}

def veri_kaydet(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def borc_yukle():
    if os.path.exists(BORC_FILE):
        with open(BORC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"borclar": []}

def borc_kaydet(data):
    with open(BORC_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Kiraci Ekle", callback_data="kiraci_ekle")],
        [InlineKeyboardButton("Kiracilari Listele", callback_data="listele")],
        [InlineKeyboardButton("Odeme Isaretle", callback_data="odeme")],
        [InlineKeyboardButton("Durum Raporu", callback_data="rapor")],
        [InlineKeyboardButton("Kiraci Ayarlari", callback_data="kiraci_ayar")],
        [InlineKeyboardButton("Borclu Listesi", callback_data="borclu_menu")],
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
        [InlineKeyboardButton("Kiraci Ayarlari", callback_data="kiraci_ayar")],
        [InlineKeyboardButton("Borclu Listesi", callback_data="borclu_menu")],
    ]
    await query.edit_message_text("Ana Menu", reply_markup=InlineKeyboardMarkup(keyboard))

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
    await update.message.reply_text("Aylik kira tutarini yazin (ornek: 750):")
    return KIRA

async def kira_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tutar = float(update.message.text.replace(",", "."))
        context.user_data["yeni_kiraci"]["kira"] = tutar
        await update.message.reply_text("Odeme gunu kac? (1-31):")
        return TARIH
    except ValueError:
        await update.message.reply_text("Gecerli bir sayi yazin (ornek: 750)")
        return KIRA

async def tarih_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gun = int(update.message.text)
        if not 1 <= gun <= 31:
            raise ValueError
        context.user_data["yeni_kiraci"]["odeme_gunu"] = gun
        await update.message.reply_text("Depozito tutarini yazin (yoksa 0 yazin):")
        return DEPOZITO
    except ValueError:
        await update.message.reply_text("1-31 arasi bir sayi yazin:")
        return TARIH

async def depozito_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        depozito = float(update.message.text.replace(",", "."))
        kiraci = context.user_data["yeni_kiraci"]
        kiraci["depozito"] = depozito
        kiraci["odendi_aylar"] = []
        kiraci["kismi_odemeler"] = {}
        kiraci["id"] = datetime.now().strftime("%Y%m%d%H%M%S")
        data = veri_yukle()
        data["kiracılar"].append(kiraci)
        veri_kaydet(data)
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        depozito_str = str(int(depozito)) + " GBP" if depozito > 0 else "Yok"
        await update.message.reply_text(
            "Kiraci eklendi!\nAd: " + kiraci["ad"] + " " + kiraci["soyad"] +
            "\nDaire: " + kiraci["daire"] +
            "\nKira: " + str(int(kiraci["kira"])) + " GBP" +
            "\nOdeme gunu: " + str(kiraci["odeme_gunu"]) +
            "\nDepozito: " + depozito_str,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    except ValueError:
                await update.message.reply_text("Gecerli bir sayi yazin (yoksa 0):")

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
        kismi = k.get("kismi_odemeler", {}).get(ay_key, 0)
        durum = "Odendi" if odendi else "Odenmedi"
        if not odendi and kismi > 0:
            durum = "Kismi: " + str(int(kismi)) + " GBP"
        kalan = k["odeme_gunu"] - bugun.day
        if not odendi and kalan < 0:
            durum = durum + " (GECIKTI " + str(abs(kalan)) + " gun)"
        depozito_str = ""
        if k.get("depozito", 0) > 0:
            depozito_str = " | Dep: " + str(int(k["depozito"])) + " GBP"
        mesaj = mesaj + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"] + "\n"
        mesaj = mesaj + str(int(k["kira"])) + " GBP | " + str(k["odeme_gunu"]) + ". gun | " + durum + depozito_str + "\n\n"
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
        kismi = k.get("kismi_odemeler", {}).get(ay_key, 0)
        if odendi:
            etiket = "[OK] " + k["ad"] + " " + k["soyad"]
        elif kismi > 0:
            etiket = "[KISMI " + str(int(kismi)) + "] " + k["ad"] + " " + k["soyad"]
        else:
            etiket = "[BEKLIYOR] " + k["ad"] + " " + k["soyad"]
        keyboard.append([InlineKeyboardButton(etiket, callback_data="toggle_" + k["id"])])
    keyboard.append([InlineKeyboardButton("Kismi Odeme Ekle", callback_data="kismi_odeme")])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Odeme Durumu - Tiklayarak tam odeme isaretle:", reply_markup=InlineKeyboardMarkup(keyboard))

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
                mesaj = k["ad"] + " " + k["soyad"] + " - tam odeme isaretlendi"
            break
    veri_kaydet(data)
    keyboard = []
    for k in data["kiracılar"]:
        odendi = ay_key in k.get("odendi_aylar", [])
        kismi = k.get("kismi_odemeler", {}).get(ay_key, 0)
        if odendi:
            etiket = "[OK] " + k["ad"] + " " + k["soyad"]
        elif kismi > 0:
            etiket = "[KISMI " + str(int(kismi)) + "] " + k["ad"] + " " + k["soyad"]
        else:
            etiket = "[BEKLIYOR] " + k["ad"] + " " + k["soyad"]
        keyboard.append([InlineKeyboardButton(etiket, callback_data="toggle_" + k["id"])])
    keyboard.append([InlineKeyboardButton("Kismi Odeme Ekle", callback_data="kismi_odeme")])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Odeme Durumu\n" + mesaj + "\n\nTiklayarak degistirin:", reply_markup=InlineKeyboardMarkup(keyboard))
async def kismi_odeme_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    if not kiracılar:
        await query.edit_message_text("Henuz kiraci yok.")
        return ConversationHandler.END
    keyboard = []
    for k in kiracılar:
        keyboard.append([InlineKeyboardButton(k["ad"] + " " + k["soyad"] + " - " + str(int(k["kira"])) + " GBP", callback_data="kismi_sec_" + k["id"])])
    keyboard.append([InlineKeyboardButton("Iptal", callback_data="ana_menu")])
    await query.edit_message_text("Kismi odeme yapan kiraciyi secin:", reply_markup=InlineKeyboardMarkup(keyboard))
    return KISMI_ID

async def kismi_kiraci_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kiraci_id = query.data.replace("kismi_sec_", "")
    context.user_data["kismi_kiraci_id"] = kiraci_id
    await query.edit_message_text("Odenen miktari yazin (GBP):")
    return KISMI_MIKTAR

async def kismi_miktar_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        miktar = float(update.message.text.replace(",", "."))
        kiraci_id = context.user_data["kismi_kiraci_id"]
        data = veri_yukle()
        ay_key = datetime.now().strftime("%Y-%m")
        ad = ""
        toplam = 0
        kira = 0
        for k in data["kiracılar"]:
            if k["id"] == kiraci_id:
                if "kismi_odemeler" not in k:
                    k["kismi_odemeler"] = {}
                mevcut = k["kismi_odemeler"].get(ay_key, 0)
                k["kismi_odemeler"][ay_key] = mevcut + miktar
                ad = k["ad"] + " " + k["soyad"]
                toplam = k["kismi_odemeler"][ay_key]
                kira = k["kira"]
                break
        veri_kaydet(data)
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await update.message.reply_text(
            "Kismi odeme eklendi!\n" + ad + "\nBu ay odenen: " + str(int(toplam)) + " / " + str(int(kira)) + " GBP\nKalan: " + str(int(kira - toplam)) + " GBP",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Gecerli bir sayi yazin:")
        return KISMI_MIKTAR

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    bugun = datetime.now()
    ay_key = bugun.strftime("%Y-%m")
    toplam = len(kiracılar)
    odenenler = sum(1 for k in kiracılar if ay_key in k.get("odendi_aylar", []))
    gecikmis = sum(1 for k in kiracılar if ay_key not in k.get("odendi_aylar", []) and k["odeme_gunu"] < bugun.day)
    toplam_kira = sum(k["kira"] for k in kiracılar)
    toplanan = sum(k["kira"] for k in kiracılar if ay_key in k.get("odendi_aylar", []))
    kismi_toplam = sum(k.get("kismi_odemeler", {}).get(ay_key, 0) for k in kiracılar if ay_key not in k.get("odendi_aylar", []))
    mesaj = "Rapor - " + bugun.strftime("%B %Y") + "\n\n"
    mesaj += "Toplam kiraci: " + str(toplam) + "\n"
    mesaj += "Tam odeme yapan: " + str(odenenler) + "\n"
    mesaj += "Gecikmiş: " + str(gecikmis) + "\n\n"
    mesaj += "Beklenen: " + str(int(toplam_kira)) + " GBP\n"
    mesaj += "Toplanan: " + str(int(toplanan)) + " GBP\n"
    mesaj += "Kismi tahsilat: " + str(int(kismi_toplam)) + " GBP\n"
    mesaj += "Bekleyen: " + str(int(toplam_kira - toplanan - kismi_toplam)) + " GBP"
    keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
    await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
async def kiraci_ayar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Kiraci Sil", callback_data="kiraci_sil_listele")],
        [InlineKeyboardButton("Kira Zammi", callback_data="kira_zam_listele")],
        [InlineKeyboardButton("Isim Degistir", callback_data="isim_degistir_listele")],
        [InlineKeyboardButton("Ana Menu", callback_data="ana_menu")],
    ]
    await query.edit_message_text("Kiraci Ayarlari:", reply_markup=InlineKeyboardMarkup(keyboard))

async def kiraci_sil_listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    if not kiracılar:
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await query.edit_message_text("Henuz kiraci yok.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = []
    for k in kiracılar:
        keyboard.append([InlineKeyboardButton("SIL: " + k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"], callback_data="sil_" + k["id"])])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Silmek istediginiz kiraciyi secin:", reply_markup=InlineKeyboardMarkup(keyboard))

async def kiraci_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kiraci_id = query.data.replace("sil_", "")
    data = veri_yukle()
    silinen_ad = ""
    yeni_liste = []
    for k in data["kiracılar"]:
        if k["id"] == kiraci_id:
            silinen_ad = k["ad"] + " " + k["soyad"]
        else:
            yeni_liste.append(k)
    data["kiracılar"] = yeni_liste
    veri_kaydet(data)
    keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
    await query.edit_message_text(silinen_ad + " silindi.", reply_markup=InlineKeyboardMarkup(keyboard))

async def kira_zam_listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    if not kiracılar:
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await query.edit_message_text("Henuz kiraci yok.", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    keyboard = []
    for k in kiracılar:
        keyboard.append([InlineKeyboardButton(k["ad"] + " " + k["soyad"] + " - " + str(int(k["kira"])) + " GBP", callback_data="zam_sec_" + k["id"])])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Kira zammi yapilacak kiraciyi secin:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ZAM_ID

async def zam_kiraci_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kiraci_id = query.data.replace("zam_sec_", "")
    context.user_data["zam_kiraci_id"] = kiraci_id
    data = veri_yukle()
    for k in data["kiracılar"]:
        if k["id"] == kiraci_id:
            await query.edit_message_text("Mevcut kira: " + str(int(k["kira"])) + " GBP\nYeni kira tutarini yazin:")
            break
    return ZAM_MIKTAR

async def zam_miktar_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        yeni_kira = float(update.message.text.replace(",", "."))
        kiraci_id = context.user_data["zam_kiraci_id"]
        data = veri_yukle()
        eski = 0
        ad = ""
        for k in data["kiracılar"]:
            if k["id"] == kiraci_id:
                eski = k["kira"]
                k["kira"] = yeni_kira
                ad = k["ad"] + " " + k["soyad"]
                break
        veri_kaydet(data)
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await update.message.reply_text(
            ad + " kira guncellendi!\n" + str(int(eski)) + " GBP -> " + str(int(yeni_kira)) + " GBP",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Gecerli bir sayi yazin:")
        return ZAM_MIKTAR

async def isim_degistir_listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = veri_yukle()
    kiracılar = data["kiracılar"]
    if not kiracılar:
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await query.edit_message_text("Henuz kiraci yok.", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    keyboard = []
    for k in kiracılar:
        keyboard.append([InlineKeyboardButton(k["ad"] + " " + k["soyad"] + " - Daire " + k["daire"], callback_data="isim_sec_" + k["id"])])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Isim degistirilecek kiraciyi secin:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ISIM_ID

async def isim_kiraci_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kiraci_id = query.data.replace("isim_sec_", "")
    context.user_data["isim_kiraci_id"] = kiraci_id
    await query.edit_message_text("Yeni adi ve soyadi yazin (ornek: Ali Yilmaz):")
    return ISIM_YENI

async def isim_yeni_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parcalar = update.message.text.strip().split(" ", 1)
    if len(parcalar) < 2:
        await update.message.reply_text("Lutfen ad ve soyad yazin (ornek: Ali Yilmaz):")
        return ISIM_YENI
    kiraci_id = context.user_data["isim_kiraci_id"]
    data = veri_yukle()
    eski = ""
    for k in data["kiracılar"]:
        if k["id"] == kiraci_id:
            eski = k["ad"] + " " + k["soyad"]
            k["ad"] = parcalar[0]
            k["soyad"] = parcalar[1]
            break
    veri_kaydet(data)
    keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
    await update.message.reply_text(
        eski + " -> " + update.message.text + " olarak guncellendi.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END
async def borclu_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Borclu Ekle", callback_data="borc_ekle")],
        [InlineKeyboardButton("Borclulari Listele", callback_data="borc_listele")],
        [InlineKeyboardButton("Odeme Isaretle", callback_data="borc_odeme")],
        [InlineKeyboardButton("Ana Menu", callback_data="ana_menu")],
    ]
    await query.edit_message_text("Borclu Listesi Menusu:", reply_markup=InlineKeyboardMarkup(keyboard))

async def borc_ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Borclu kisinin adini yazin:")
    return BORC_AD

async def borc_ad_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["yeni_borc"] = {"ad": update.message.text}
    await update.message.reply_text("Borcun miktarini yazin (ornek: 500):")
    return BORC_MIKTAR

async def borc_miktar_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        miktar = float(update.message.text.replace(",", "."))
        context.user_data["yeni_borc"]["miktar"] = miktar
        await update.message.reply_text("Geri odeme tarihini yazin (ornek: 15/06/2025):")
        return BORC_TARIH
    except ValueError:
        await update.message.reply_text("Gecerli bir sayi yazin (ornek: 500)")
        return BORC_MIKTAR

async def borc_tarih_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tarih_str = update.message.text.strip()
        datetime.strptime(tarih_str, "%d/%m/%Y")
        borc = context.user_data["yeni_borc"]
        borc["tarih"] = tarih_str
        borc["odendi"] = False
        borc["id"] = datetime.now().strftime("%Y%m%d%H%M%S")
        data = borc_yukle()
        data["borclar"].append(borc)
        borc_kaydet(data)
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await update.message.reply_text(
            "Borclu eklendi!\nAd: " + borc["ad"] + "\nMiktar: " + str(int(borc["miktar"])) + " GBP\nVade: " + borc["tarih"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Gecersiz tarih! Ornek: 15/06/2025")
        return BORC_TARIH

async def borc_listele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = borc_yukle()
    borclar = data["borclar"]
    if not borclar:
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await query.edit_message_text("Henuz borclu yok.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    bugun = datetime.now()
    mesaj = "Borclu Listesi\n\n"
    for b in borclar:
        durum = "Odendi" if b["odendi"] else "Bekliyor"
        try:
            vade = datetime.strptime(b["tarih"], "%d/%m/%Y")
            if not b["odendi"] and vade < bugun:
                kalan = (bugun - vade).days
                durum = "GECIKTI (" + str(kalan) + " gun)"
        except:
            pass
        mesaj = mesaj + b["ad"] + " - " + str(int(b["miktar"])) + " GBP\nVade: " + b["tarih"] + " | " + durum + "\n\n"
    keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
    await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))

async def borc_odeme_listesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = borc_yukle()
    borclar = data["borclar"]
    if not borclar:
        keyboard = [[InlineKeyboardButton("Ana Menu", callback_data="ana_menu")]]
        await query.edit_message_text("Henuz borclu yok.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = []
    for b in borclar:
        if b["odendi"]:
            etiket = "[OK] " + b["ad"] + " - " + str(int(b["miktar"])) + " GBP"
        else:
            etiket = "[BEKLIYOR] " + b["ad"] + " - " + str(int(b["miktar"])) + " GBP"
        keyboard.append([InlineKeyboardButton(etiket, callback_data="borc_toggle_" + b["id"])])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Borclu Odeme Durumu - Tiklayarak degistirin:", reply_markup=InlineKeyboardMarkup(keyboard))

async def borc_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    borc_id = query.data.replace("borc_toggle_", "")
    data = borc_yukle()
    mesaj = ""
    for b in data["borclar"]:
        if b["id"] == borc_id:
            b["odendi"] = not b["odendi"]
            durum = "odendi isaretlendi" if b["odendi"] else "geri alindi"
            mesaj = b["ad"] + " - " + durum
            break
    borc_kaydet(data)
    keyboard = []
    for b in data["borclar"]:
        if b["odendi"]:
            etiket = "[OK] " + b["ad"] + " - " + str(int(b["miktar"])) + " GBP"
        else:
            etiket = "[BEKLIYOR] " + b["ad"] + " - " + str(int(b["miktar"])) + " GBP"
        keyboard.append([InlineKeyboardButton(etiket, callback_data="borc_toggle_" + b["id"])])
    keyboard.append([InlineKeyboardButton("Ana Menu", callback_data="ana_menu")])
    await query.edit_message_text("Borclu Odeme Durumu\n" + mesaj + "\n\nTiklayarak degistirin:", reply_markup=InlineKeyboardMarkup(keyboard))
def main():
    print("main() cagrildi")
    app = Application.builder().token(TOKEN).build()

    kiraci_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(kiraci_ekle_baslat, pattern="^kiraci_ekle$")],
        states={
            AD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ad_al)],
            SOYAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, soyad_al)],
            DAIRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, daire_al)],
            KIRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, kira_al)],
            TARIH: [MessageHandler(filters.TEXT & ~filters.COMMAND, tarih_al)],
            DEPOZITO: [MessageHandler(filters.TEXT & ~filters.COMMAND, depozito_al)],
        },
        fallbacks=[CommandHandler("iptal", iptal)],
    )

    borc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(borc_ekle_baslat, pattern="^borc_ekle$")],
        states={
            BORC_AD: [MessageHandler(filters.TEXT & ~filters.COMMAND, borc_ad_al)],
            BORC_MIKTAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, borc_miktar_al)],
            BORC_TARIH: [MessageHandler(filters.TEXT & ~filters.COMMAND, borc_tarih_al)],
        },
        fallbacks=[CommandHandler("iptal", iptal)],
    )

    zam_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(kira_zam_listele, pattern="^kira_zam_listele$")],
        states={
            ZAM_ID: [CallbackQueryHandler(zam_kiraci_sec, pattern="^zam_sec_")],
            ZAM_MIKTAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, zam_miktar_al)],
        },
        fallbacks=[CommandHandler("iptal", iptal)],
    )

    isim_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(isim_degistir_listele, pattern="^isim_degistir_listele$")],
        states={
            ISIM_ID: [CallbackQueryHandler(isim_kiraci_sec, pattern="^isim_sec_")],
            ISIM_YENI: [MessageHandler(filters.TEXT & ~filters.COMMAND, isim_yeni_al)],
        },
        fallbacks=[CommandHandler("iptal", iptal)],
    )

    kismi_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(kismi_odeme_baslat, pattern="^kismi_odeme$")],
        states={
            KISMI_ID: [CallbackQueryHandler(kismi_kiraci_sec, pattern="^kismi_sec_")],
            KISMI_MIKTAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, kismi_miktar_al)],
        },
        fallbacks=[CommandHandler("iptal", iptal)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(kiraci_conv)
    app.add_handler(borc_conv)
    app.add_handler(zam_conv)
    app.add_handler(isim_conv)
    app.add_handler(kismi_conv)
    app.add_handler(CallbackQueryHandler(menu, pattern="^ana_menu$"))
    app.add_handler(CallbackQueryHandler(listele, pattern="^listele$"))
    app.add_handler(CallbackQueryHandler(odeme_listesi, pattern="^odeme$"))
    app.add_handler(CallbackQueryHandler(rapor, pattern="^rapor$"))
    app.add_handler(CallbackQueryHandler(odeme_toggle, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(kiraci_ayar_menu, pattern="^kiraci_ayar$"))
    app.add_handler(CallbackQueryHandler(kiraci_sil_listele, pattern="^kiraci_sil_listele$"))
    app.add_handler(CallbackQueryHandler(kiraci_sil, pattern="^sil_"))
    app.add_handler(CallbackQueryHandler(borclu_menu, pattern="^borclu_menu$"))
    app.add_handler(CallbackQueryHandler(borc_listele, pattern="^borc_listele$"))
    app.add_handler(CallbackQueryHandler(borc_odeme_listesi, pattern="^borc_odeme$"))
    app.add_handler(CallbackQueryHandler(borc_toggle, pattern="^borc_toggle_"))
    print("Bot polling basliyor...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("KRITIK HATA:")
        print(traceback.format_exc())
        import time
        time.sleep(300)
