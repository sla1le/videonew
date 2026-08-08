# -*- coding: utf-8 -*-
"""Готовит изображения из пакета владельца канала в единый вид.
Портреты переводятся в высококонтрастный серый, обложки остаются цветными.

Запуск: python3 build/prep_img.py
Пакет с исходными картинками в git не хранится, путь в PACK.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = "/data/echo/assets/packet/ECHORATE_ALL_PHOTOS_PACKET"
V1 = os.path.join(PACK, "01_VIPERR_vs_THRILL_PILL")
PREV = os.path.join(PACK, "99_PREVIOUS_PACKET")
CUP_A = os.path.join(PACK, "03_ALBUM_WORLD_CUP_R32", "covers")
CUP_B = os.path.join(PREV, "03_ALBUM_WORLD_CUP_R32", "covers")

OUT_P = os.path.join(HERE, "img", "people")
OUT_C = os.path.join(HERE, "img", "covers")
os.makedirs(OUT_P, exist_ok=True)
os.makedirs(OUT_C, exist_ok=True)

fails = []


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        fails.append(" ".join(args[:3]) + " :: " + p.stderr.strip()[:180])
        return False
    return True


def gray(src, dst, w, h, grav="north", bright="100,100"):
    if not os.path.exists(src):
        fails.append("нет файла: " + src)
        return
    run([
        "magick", src,
        "-colorspace", "Gray",
        "-modulate", bright,
        "-contrast-stretch", "1.5%x1.5%",
        "-resize", "%dx%d^" % (w, h),
        "-gravity", grav,
        "-extent", "%dx%d" % (w, h),
        "+repage",
        "-unsharp", "0x1+0.75+0",
        dst,
    ])


def color(src, dst, w, h):
    if not os.path.exists(src):
        fails.append("нет файла: " + src)
        return
    run([
        "magick", src,
        "-resize", "%dx%d^" % (w, h),
        "-gravity", "center",
        "-extent", "%dx%d" % (w, h),
        "+repage",
        "-unsharp", "0x1+0.5+0",
        dst,
    ])


# ---------------------------------------------------------------- люди
viperr_sq = os.path.join(V1, "VIPERR", "VIPERR_Kai_Angel_9mice_2023_The_Flow_square.jpg")
viperr_wd = os.path.join(V1, "VIPERR", "VIPERR_Kai_Angel_9mice_2024_Zvuk_horizontal.jpg")
viperr_lv = os.path.join(V1, "VIPERR", "VIPERR_live_2025_Stadium_02.jpeg")
viperr_l1 = os.path.join(V1, "VIPERR", "VIPERR_live_2025_Stadium_01.jpeg")
thrill_rl = os.path.join(V1, "THRILL_PILL", "THRILL_PILL_OTKROVENIYA_release_image.jpg")
thrill_st = os.path.join(V1, "THRILL_PILL", "THRILL_PILL_Grustnaya_Pesnya_video_still.jpg")
thrill_pt = os.path.join(PREV, "01_VIPERR_vs_THRILL_PILL", "portraits", "THRILL_PILL_portrait.jpg")
hm2 = os.path.join(V1, "covers", "VIPERR_Heavy_Metal_2_cover_2000.webp")

gray(viperr_sq, os.path.join(OUT_P, "viperr_head.png"), 456, 604, "center")
gray(thrill_pt, os.path.join(OUT_P, "thrill_head.png"), 456, 604, "north")
gray(viperr_wd, os.path.join(OUT_P, "viperr_wide.png"), 936, 470, "center")
gray(thrill_st, os.path.join(OUT_P, "thrill_wide.png"), 936, 470, "center")
gray(viperr_lv, os.path.join(OUT_P, "viperr_live.png"), 456, 604, "center")
gray(viperr_l1, os.path.join(OUT_P, "viperr_live_wide.png"), 936, 470, "center")
gray(viperr_sq, os.path.join(OUT_P, "viperr_sq.png"), 380, 380, "center")
gray(thrill_pt, os.path.join(OUT_P, "thrill_sq.png"), 380, 380, "north")
color(hm2, os.path.join(OUT_C, "viperr_hm2.png"), 560, 560)
color(thrill_rl, os.path.join(OUT_C, "thrill_otkroveniya.png"), 560, 560)

# ---------------------------------------------------------------- обложки
COVERS = [
    (CUP_B, "M01A_\u0421\u043a\u0440\u0438\u043f\u0442\u043e\u043d\u0438\u0442_\u0414\u043e\u043c_\u0441_\u043d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u044b\u043c\u0438_\u044f\u0432\u043b\u0435\u043d\u0438\u044f\u043c\u0438.jpg", "skryptonite_dsny"),
    (CUP_B, "M01B_\u0414\u0435\u0446\u043b_\u041a\u0442\u043e_\u0442\u044b.webp", "decl_ktoty"),
    (CUP_A, "M02A_\u041b\u0421\u041f_Tragic_City.jpg", "lsp_tragiccity"),
    (CUP_B, "M03A_ATL_\u041c\u0430\u0440\u0430\u0431\u0443.jpg", "atl_marabu"),
    (CUP_B, "M03B_\u041f\u0435\u0442\u043b\u044f_\u041f\u0440\u0438\u0441\u0442\u0440\u0430\u0441\u0442\u0438\u044f_\u0424\u043e\u0431\u043e\u0441.jpg", "petlya_fobos"),
    (CUP_B, "M04B_IC3PEAK_\u0421\u043a\u0430\u0437\u043a\u0430.jpg", "ic3peak_skazka"),
    (CUP_B, "M05A_Oxxxymiron_\u0413\u043e\u0440\u0433\u043e\u0440\u043e\u0434.webp", "oxxxymiron_gorgorod"),
    (CUP_B, "M05B_4_\u041f\u043e\u0437\u0438\u0446\u0438\u0438_\u0411\u0440\u0443\u043d\u043e_\u042f_\u0437\u0430\u043a\u0430\u0437\u0430\u043d.webp", "4pb_zakazan"),
    (CUP_B, "M06A_\u0417\u0435\u043c\u0444\u0438\u0440\u0430_\u041f\u0440\u043e\u0441\u0442\u0438_\u043c\u0435\u043d\u044f_\u043c\u043e\u044f_\u043b\u044e\u0431\u043e\u0432\u044c.jpg", "zemfira_pmml"),
    (CUP_B, "M07A_25-17_\u0420\u0443\u0441\u0441\u043a\u0438\u0439_\u043f\u043e\u0434\u043e\u0440\u043e\u0436\u043d\u0438\u043a.jpg", "a2517_podorozhnik"),
    (CUP_B, "M07B_\u0413\u0443\u0444_\u0413\u043e\u0440\u043e\u0434_\u0434\u043e\u0440\u043e\u0433.webp", "guf_goroddorog"),
    (CUP_B, "M08B_Mnogoznaal_\u0413\u043e\u0441\u0442\u0438\u043d\u0438\u0446\u0430_\u041a\u043e\u0441\u043c\u043e\u0441.jpg", "mnogoznaal_kosmos"),
    (CUP_B, "M09A_Boulevard_Depo_OLD_BLOOD.jpg", "depo_oldblood"),
    (CUP_B, "M09B_MONATIK_\u0417\u0432\u0443\u0447\u0438\u0442.jpg", "monatik_zvuchit"),
    (CUP_B, "M11A_t.A.T.u._200_\u043f\u043e_\u0432\u0441\u0442\u0440\u0435\u0447\u043d\u043e\u0439.jpg", "tatu_200"),
]

made = []
for folder, name, key in COVERS:
    src = os.path.join(folder, name)
    dst = os.path.join(OUT_C, key + ".png")
    color(src, dst, 560, 560)
    if os.path.exists(dst):
        made.append(key)

# мозаика для обложки кубка
tiles = [os.path.join(OUT_C, k + ".png") for k in made]
if len(tiles) >= 15:
    run(["magick", "montage"] + tiles[:15] + [
        "-tile", "5x3", "-geometry", "216x216+0+0", "-background", "#0E0E0E",
        "-colorspace", "Gray", "-modulate", "78,100",
        os.path.join(OUT_C, "mosaic.png"),
    ])

print("обложек готово:", len(made))
print("ключи:", ", ".join(made))
for f in fails:
    print("СБОЙ:", f)
if fails:
    sys.exit(1)
