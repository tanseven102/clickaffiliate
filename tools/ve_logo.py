#!/usr/bin/env python3
"""Vẽ logo PNG (icon 192/512) + ảnh chia sẻ og.png 1200x630 — cùng hình với assets/logo.svg."""
import os
from PIL import Image, ImageDraw, ImageFont

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(GOC, "assets")


def dau(co):
    """Vẽ dấu logo ở cỡ co×co (vẽ to gấp 4 rồi thu nhỏ cho mượt)."""
    S = co * 4
    k = S / 64
    nen = Image.new("RGBA", (S, S))
    # nền chuyển màu chéo #3B82F6 → #1D4ED8
    g = Image.new("RGBA", (S, S))
    px = g.load()
    for y in range(S):
        for x in range(S):
            t = (x + y) / (2 * S)
            px[x, y] = (int(59 + (29 - 59) * t), int(130 + (78 - 130) * t), int(246 + (216 - 246) * t), 255)
    mask = Image.new("L", (S, S))
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(16 * k), fill=255)
    nen.paste(g, (0, 0), mask)
    d = ImageDraw.Draw(nen)
    w = int(3.2 * k)
    for (x1, y1, x2, y2) in [(22, 13, 22, 19), (11.5, 22.5, 17.5, 22.5), (14.5, 14.5, 18.7, 18.7), (29.5, 14.5, 25.3, 18.7)]:
        d.line([(x1 * k, y1 * k), (x2 * k, y2 * k)], fill=(191, 219, 254, 255), width=w)
        for (x, y) in [(x1, y1), (x2, y2)]:
            d.ellipse([x * k - w / 2, y * k - w / 2, x * k + w / 2, y * k + w / 2], fill=(191, 219, 254, 255))
    tro = [(24, 24), (49, 33.5), (38.4, 37.2), (46.2, 45), (41.6, 49.6), (33.8, 41.8), (30, 52)]
    d.polygon([(x * k, y * k) for x, y in tro], fill="white")
    return nen.resize((co, co), Image.LANCZOS)


def font(co, dam=True):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if dam else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/mnt/c/Windows/Fonts/segoeuib.ttf" if dam else "/mnt/c/Windows/Fonts/segoeui.ttf"]:
        if os.path.exists(f):
            return ImageFont.truetype(f, co)
    return ImageFont.load_default()


for co in (192, 512):
    dau(co).save(os.path.join(A, f"icon-{co}.png"))

og = Image.new("RGB", (1200, 630), (250, 249, 246))
d = ImageDraw.Draw(og)
og.paste(dau(150), (90, 150), dau(150))
d.text((270, 160), "Click", font=font(96), fill=(13, 27, 51))
x = 270 + d.textlength("Click", font=font(96))
d.text((x, 160), "Affiliate", font=font(96), fill=(37, 99, 235))
d.text((92, 350), "Affiliate programs worth promoting,", font=font(46, False), fill=(13, 27, 51))
d.text((92, 412), "ranked every day.", font=font(46, False), fill=(96, 116, 144))
d.rounded_rectangle([92, 500, 572, 556], radius=28, fill=(238, 243, 255))
d.text((118, 512), "Commission · Cookie · Payout", font=font(26), fill=(37, 99, 235))
og.save(os.path.join(A, "og.png"), optimize=True)
print("xong")
