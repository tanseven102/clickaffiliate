#!/usr/bin/env python3
"""ClickAffiliate — dựng toàn bộ trang tĩnh từ dữ liệu chương trình affiliate.

Chạy:  python3 build.py [--nguon .nguon/programs] [--ra site] [--dang 4]
  --dang N : hôm nay đăng thêm N bài blog mới (máy chạy mỗi ngày dùng số này)
Biến môi trường SITE_URL: địa chỉ gốc trang, vd https://clickaffiliate.net
(mặc định https://tanseven102.github.io/clickaffiliate).
"""
import argparse, datetime as dt, glob, hashlib, html, json, os, re, shutil
from email.utils import format_datetime
from urllib.parse import urlparse

import yaml

import noi_dung_vi

GOC = os.path.dirname(os.path.abspath(__file__))
SITE_URL = os.environ.get("SITE_URL", "https://tanseven102.github.io/clickaffiliate").rstrip("/")
P = urlparse(SITE_URL).path.rstrip("/")          # tiền tố đường dẫn ("" khi có tên miền riêng)
TEN = "ClickAffiliate"
CHU = "Le Van Tan (Tan-Seven)"
EMAIL = "tanseven5@gmail.com"
# link affiliate riêng của anh Tân (Affitor, join 29/10/2026) — nút "Try …" trên trang chương trình đi qua link này
LINK_AFF = {"velvet": "https://velvet.salon/?aff=onTMkQM", "landerlab": "https://landerlab.io/?aff=4EivyrF"}
INDEXNOW = "c1a7f3e9b2d84c6a9e0f5b7d3a8c2e41"  # khoá IndexNow (công khai), báo Bing/Copilot/ChatGPT tìm trang mới
# mã xác minh Google Search Console (biến GSC trong repo) — có thì gắn thẻ meta
GSC = f'<meta name="google-site-verification" content="{os.environ["GSC"]}">' if os.environ.get("GSC") else ""
HOM_NAY = dt.date.fromisoformat(os.environ.get("NGAY", dt.date.today().isoformat()))
REPO = "https://github.com/tanseven102/clickaffiliate"
NGUON_DL = "https://github.com/Affitor/open-affiliate"
BO_TRANG_THAI = {"discontinued", "no_program"}   # không còn chương trình — bỏ hẳn
KHONG_XEP = {"paused"}                            # còn trang nhưng không xếp hạng

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def doc_json(duong, mac_dinh):
    try:
        with open(duong, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return mac_dinh


def ghi_json(duong, dl):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(dl, f, ensure_ascii=False, indent=1, sort_keys=True)


def ngay(v):
    if not v:
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def chon(khoa, *cac_cau):
    """Chọn một câu theo băm của khoá — cùng khoá luôn ra cùng câu, khác khoá ra câu khác."""
    h = int(hashlib.md5(khoa.encode()).hexdigest(), 16)
    return cac_cau[h % len(cac_cau)]


# ───────────────────────── đọc + chấm điểm ─────────────────────────

def thang_tu_thoi_han(d):
    if not d:
        return 0
    d = str(d).lower()
    if "lifetime" in d:
        return 999
    m = re.search(r"(\d+)\s*(month|year)", d)
    if not m:
        return 0
    return int(m.group(1)) * (12 if m.group(2) == "year" else 1)


def cham_diem(p):
    c = p["c"]
    # 1. Hoa hồng — tối đa 40
    if c["mode"] == "flat" and c["value"]:
        hh = min(c["value"] / 150, 1) * 30
    elif c["value"]:
        hh = min(c["value"] / 50, 1) * 30
    else:
        hh = 9
    if c["type"] == "recurring":
        t = thang_tu_thoi_han(c["duration"])
        hh += 10 if t >= 999 else 8 if t >= 24 else 7 if t >= 12 else 5
    elif c["type"] in ("hybrid", "tiered"):
        hh += 4
    hh = min(hh, 40)
    # 2. Cookie — tối đa 15
    cd = p["cookie"]
    ck = 3 if not cd else 15 if cd >= 90 else 12 if cd >= 60 else 9 if cd >= 30 else 5
    # 3. Độ tin — tối đa 25
    tin = 14 if p["verified"] else 4
    if p["status"] == "active":
        tin += 5
    lv = p["last_verified"]
    if p["verified"] and lv and (HOM_NAY - lv).days <= 60:
        tin += 6
    elif p["verified"] and lv and (HOM_NAY - lv).days <= 180:
        tin += 3
    # 4. Điều khoản dễ — tối đa 20
    dk = {"auto": 8, "automatic": 8, "manual": 5, "invite-only": 1}.get(p["approval"], 3)
    tan = (p["payout"].get("frequency") or "")
    dk += 5 if tan in ("monthly", "net-15", "net-30", "weekly") else 3 if tan else 2
    mn = p["payout"].get("minimum")
    dk += 3 if (mn is None or (isinstance(mn, (int, float)) and mn <= 50)) else 1
    dk += 2 if p["materials"] else 0
    dk += 2 if len(p["restrictions"]) <= 2 else 0
    dk = min(dk, 20)
    tong = round(hh + ck + tin + dk)
    p["diem"] = tong
    p["chia"] = [("Commission", round(hh), 40), ("Cookie window", ck, 15), ("Trust & freshness", tin, 25), ("Easy terms", dk, 20)]
    p["hang"] = "A+" if tong >= 88 else "A" if tong >= 78 else "B" if tong >= 66 else "C" if tong >= 54 else "D"


def thuong(s):
    """Viết thường giữa câu nhưng giữ chữ viết tắt (AI, CRM, SaaS…)."""
    return " ".join(w if (sum(ch.isupper() for ch in w) > 1) else w.lower() for w in s.split())


def giua_cau(s):
    return s[:1].lower() + s[1:] if s[:3] in ("Up ", "Var") else s


def nhan_hoa_hong(c):
    rate = c["rate"] or "Varies"
    if c["type"] == "recurring":
        d = c["duration"]
        return f"{rate} recurring" + (f" · {d}" if d else "")
    if c["type"] == "one-time":
        return f"{rate} one-time"
    return f"{rate} {c['type']}"


def doc_chuong_trinh(thu_muc):
    ds = []
    for f in sorted(glob.glob(os.path.join(thu_muc, "*.yaml"))):
        try:
            r = yaml.safe_load(open(f, encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(r, dict) or not r.get("slug") or not r.get("name"):
            continue
        st = r.get("status") or ""
        if st in BO_TRANG_THAI:
            continue
        cm = r.get("commission") or {}
        val = cm.get("value")
        p = {
            "slug": slugify(r["slug"]), "name": str(r["name"]).strip(), "url": r.get("url") or "",
            "cat": r.get("category") or "Other", "tags": [str(t) for t in (r.get("tags") or [])][:8],
            "c": {"rate": str(cm.get("rate") or "").strip(), "type": cm.get("type") or "", "mode": cm.get("mode") or "",
                  "value": val if isinstance(val, (int, float)) else None, "duration": cm.get("duration"),
                  "conditions": cm.get("conditions") or ""},
            "cookie": r.get("cookie_days") if isinstance(r.get("cookie_days"), (int, float)) else None,
            "payout": r.get("payout") or {}, "approval": r.get("approval") or "",
            "approval_time": r.get("approval_time") or "", "network": r.get("network") or "",
            "verified": bool(r.get("verified")), "status": st,
            "desc": (r.get("description") or "").strip(), "signup": r.get("signup_url") or r.get("url") or "",
            "restrictions": [str(x) for x in (r.get("restrictions") or [])],
            "materials": bool(r.get("marketing_materials")), "attribution": r.get("attribution") or "",
            "created": ngay(r.get("created_at")), "last_verified": ngay(r.get("last_verified_at") or r.get("verified_at")),
            "use_cases": [str(x) for x in ((r.get("agents") or {}).get("use_cases") or [])][:4],
        }
        p["domain"] = urlparse(p["url"]).netloc.replace("www.", "") if p["url"] else ""
        p["cat_slug"] = slugify(p["cat"])
        p["nhan"] = nhan_hoa_hong(p["c"])
        ngan = re.split(r"(?<=[.!?])\s", p["desc"].split("Affiliate program:")[0].strip())[0]
        if len(ngan) > 180:                       # cắt ở chỗ hết từ, không cắt giữa chữ
            ngan = ngan[:178].rsplit(" ", 1)[0].rstrip(",;:-") + "…"
        p["ngan"] = ngan + ("." if ngan and ngan[-1] not in ".!?…" else "")
        cham_diem(p)
        ds.append(p)
    # trùng slug: giữ bản đầu
    thay = {}
    for p in ds:
        thay.setdefault(p["slug"], p)
    return list(thay.values())


# ───────────────────────── khung HTML ─────────────────────────

def u(duong=""):
    return f"{P}/{duong}" if duong else f"{P}/"


def logo_ct(p, co=34):
    chu = e(p["name"][:1].upper())
    if not p["domain"]:
        return f'<span class="chu-cai">{chu}</span>'
    return (f'<img class="logo" loading="lazy" width="{co}" height="{co}" alt="" '
            f'src="https://www.google.com/s2/favicons?domain={e(p["domain"])}&amp;sz=64" '
            f'onerror="this.outerHTML=\'<span class=chu-cai>{chu}</span>\'">')


def diem_html(p):
    g = p["hang"].replace("+", "p")
    return f'<span class="diem">{p["diem"]}<i class="g-{g}">{e(p["hang"])}</i></span>'


# nút Tiếng Việt: mở đúng trang hiện tại qua Google Dịch; đang ở bản dịch thì nút thành "English"
NGON_NGU_JS = r"""<script>(function(){var a=document.getElementById("ngon-ngu"),h=location.hostname;
if(location.pathname.indexOf("/vi/")>-1){a.textContent="🌐 English";a.title="English";a.href=SITE+"/";}
else if(h.endsWith(".translate.goog")){a.textContent="🌐 English";a.title="Back to English";a.href=SITE+location.pathname+location.hash;}
else{a.href="https://"+h.replace(/-/g,"--").replace(/\./g,"-")+".translate.goog"+location.pathname+"?_x_tr_sl=en&_x_tr_tl=vi&_x_tr_hl=vi"+location.hash;}})();</script>""".replace("SITE", json.dumps(SITE_URL))


def khung(tieu_de, mo_ta, duong, than, *, ld=None, nav="", og_type="website", anh_og="assets/og.png", md=False, lang="en"):
    can = f"{SITE_URL}/{duong}"
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (ld or []))
    muc = [("rankings/", "Rankings"), ("programs/", "Programs"), ("categories/", "Categories"), ("new/", "New"), ("blog/", "Blog"), ("about/", "About")]
    nav_html = "".join(f'<a href="{u(d)}"{" class=on" if nav == d else ""}>{t}</a>' for d, t in muc)
    full = tieu_de if TEN in tieu_de else f"{tieu_de} · {TEN}"
    return f"""<!doctype html>
<html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(mo_ta)}">
<link rel="canonical" href="{e(can)}">{GSC}
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{TEN}">
<meta property="og:title" content="{e(full)}"><meta property="og:description" content="{e(mo_ta)}">
<meta property="og:url" content="{e(can)}"><meta property="og:image" content="{SITE_URL}/{anh_og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{u('assets/logo.svg')}" type="image/svg+xml"><link rel="apple-touch-icon" href="{u('assets/icon-192.png')}">
<link rel="alternate" type="application/rss+xml" title="{TEN} blog" href="{u('feed.xml')}">{f'<link rel="alternate" type="text/markdown" href="{can}index.md">' if md else ""}
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{u('assets/style.css')}?v={HOM_NAY.isoformat()}">
{lds}
</head><body>
<header class="top"><div class="wrap">
<a class="brand" href="{u()}"><img src="{u('assets/logo.svg')}" alt="{TEN} logo" width="34" height="34"><b>Click<span>Affiliate</span></b></a>
<button class="menu-btn" aria-label="Menu" onclick="document.querySelector('.nav').classList.toggle('mo')">☰</button>
<nav class="nav">{nav_html}<a class="lang" id="ngon-ngu" href="#" title="Đọc trang bằng tiếng Việt">🌐 Tiếng Việt</a><a class="btn chinh" style="color:#fff;padding:7px 13px" href="{u('subscribe/')}">Subscribe</a></nav>
</div></header>
<main>{than}</main>
<footer><div class="wrap">
<div><a class="brand" href="{u()}"><img src="{u('assets/logo.svg')}" alt="" width="30" height="30"><b>Click<span>Affiliate</span></b></a>
<p>The affiliate program directory that ranks programs by real terms — commission, cookie, payout and approval — and updates every day. Rankings are never paid.</p></div>
<div><h4>Directory</h4><a href="{u('rankings/')}">Top rankings</a><a href="{u('programs/')}">All programs</a><a href="{u('categories/')}">Categories</a><a href="{u('new/')}">New programs</a></div>
<div><h4>Read</h4><a href="{u('vi/')}">🇻🇳 Bài viết tiếng Việt</a><a href="{u('subscribe/')}">Weekly newsletter</a><a href="{u('blog/')}">Blog</a><a href="{u('about/')}#clickscore">How ClickScore works</a><a href="{u('feed.xml')}">RSS feed</a></div>
<div><h4>Project</h4><a href="{u('about/')}">About</a><a href="{u('about/')}#submit">Submit a program</a><a href="{u('about/')}#disclosure">Disclosure</a><a href="{u('contact/')}">Contact</a><a href="{u('privacy/')}">Privacy</a><a href="{u('terms/')}">Terms</a></div>
</div><div class="wrap duoi">© {HOM_NAY.year} {TEN} by Tan-Seven · All rights reserved · Updated {HOM_NAY.strftime("%B %-d, %Y")}</div></footer>
{NGON_NGU_JS}
<script src="{u('assets/dangky.js')}?v={HOM_NAY.isoformat()}" defer></script>
</body></html>"""


def ghi(ra, duong, noi_dung):
    f = os.path.join(ra, duong, "index.html") if not duong.endswith((".xml", ".txt", ".json", ".html", ".md")) else os.path.join(ra, duong)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(noi_dung)


def sang_md(h):
    """Chuyển HTML bài viết sang Markdown gọn cho máy AI đọc."""
    h = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: f"[{m.group(2)}]({m.group(1) if m.group(1).startswith('http') else SITE_URL + m.group(1)[len(P):]})", h)
    h = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n\n## \1\n\n", h)
    h = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n\n### \1\n\n", h)
    h = re.sub(r"<li>(.*?)</li>", r"\n- \1", h)
    h = re.sub(r"</?(b|strong)>", "**", h)
    def bang(m):
        dong = [re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r) for r in re.findall(r"<tr>(.*?)</tr>", m.group(0))]
        if not dong:
            return ""
        if "<thead>" not in m.group(0):
            dong.insert(0, ["", ""][:len(dong[0])] or [""])
        n = max(len(r) for r in dong)
        hang = ["| " + " | ".join(r + [""] * (n - len(r))) + " |" for r in dong]
        return "\n\n" + "\n".join([hang[0], "|" + "---|" * n] + hang[1:]) + "\n\n"
    h = re.sub(r"<table>.*?</table>", bang, h, flags=re.S)
    h = re.sub(r"</p>|<br>", "\n\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = html.unescape(h)
    return re.sub(r"\n{3,}", "\n\n", h).strip() + "\n"


def vun(*phan):
    """BreadcrumbList cho JSON-LD."""
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, "item": f"{SITE_URL}/{d}"} for i, (t, d) in enumerate(phan)]}


DM_CHINH = ["AI", "Marketing", "Productivity", "Developer Tools", "Sales", "Design", "E-Commerce", "Finance"]


def hop_dk(src, tieu="Get the best new affiliate programs every week",
           mo="One short email every Monday: newly added programs, biggest ranking movers and the highest-paying recurring offers. Free, no spam.",
           chon_dm=False, id_=""):
    """Khối đăng ký bản tin — dùng ở trang chủ, cuối bài, trang /subscribe/."""
    chon = ('<div class="dk-chon">' + "".join(f'<label><input type="checkbox" name="interest" value="{e(c)}">{e(c)}</label>' for c in DM_CHINH) + "</div>") if chon_dm else ""
    return f"""<div class="card dk"{f' id="{id_}"' if id_ else ''}><div><h2>{tieu}</h2><p>{mo}</p></div>
<form class="dk-form" data-src="{e(src)}" novalidate>{chon}<div class="dk-hang"><input type="email" name="email" placeholder="you@example.com" autocomplete="email" required aria-label="Email address">
<button class="btn chinh" type="submit">Subscribe</button></div><input class="bay" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
<div class="dk-tb">Unsubscribe anytime. We never share your email.</div></form></div>"""


def bang_xep(ds, bat_dau=1, di_chuyen=None, co_dm=True):
    hang = []
    for i, p in enumerate(ds, bat_dau):
        mv = ""
        if di_chuyen is not None:
            d = di_chuyen.get(p["slug"])
            mv = ('<span class="pill ok">NEW</span>' if d is None else
                  f'<span class="pill ok">▲{d}</span>' if d > 0 else f'<span class="pill do">▼{-d}</span>' if d < 0 else
                  '<span class="pill">–</span>')
            mv = f'<td class="an-mobile">{mv}</td>'
        ver = ' <span class="pill ok">✓ verified</span>' if p["verified"] else ""
        dm = f'<td class="an-mobile"><a class="pill xanh" href="{u("categories/" + p["cat_slug"] + "/")}">{e(p["cat"])}</a></td>' if co_dm else ""
        hang.append(f"""<tr><td class="so{' top3' if i <= 3 else ''}">#{i}</td>
<td><a class="ten" href="{u('programs/' + p['slug'] + '/')}">{logo_ct(p)}<span><b>{e(p['name'])}</b>{ver}<small>{e(p['ngan'])}</small></span></a></td>
<td>{e(p['nhan'])}</td><td class="an-mobile">{f"{int(p['cookie'])} days" if p['cookie'] else '—'}</td>{dm}{mv}
<td>{diem_html(p)}</td></tr>""")
    dau = ('<th>#</th><th>Program</th><th>Commission</th><th class="an-mobile">Cookie</th>'
           + ('<th class="an-mobile">Category</th>' if co_dm else "")
           + ('<th class="an-mobile">24h</th>' if di_chuyen is not None else "") + "<th>ClickScore</th>")
    return f'<div class="card bang-cuon"><table class="rank"><thead><tr>{dau}</tr></thead><tbody>{"".join(hang)}</tbody></table></div>'


def the_ct(p, nhan_phu=""):
    ver = '<span class="pill ok">✓ verified</span>' if p["verified"] else ""
    return f"""<a class="card the-ct" href="{u('programs/' + p['slug'] + '/')}">
<div class="dau"><span class="ten">{logo_ct(p)}<b>{e(p['name'])}</b></span>{diem_html(p)}</div>
<p>{e(p['ngan'])}</p>
<div class="hang"><span class="pill xanh">{e(p['nhan'])}</span>{f'<span class="pill">{int(p["cookie"])}d cookie</span>' if p['cookie'] else ''}{ver}{nhan_phu}</div></a>"""


# ───────────────────────── bài viết tự động ─────────────────────────

def bang_so_lieu(ds):
    r = "".join(f"<tr><td><a href=\"{u('programs/' + p['slug'] + '/')}\">{e(p['name'])}</a></td><td>{e(p['nhan'])}</td>"
                f"<td>{f'{int(p['cookie'])} days' if p['cookie'] else '—'}</td><td>{p['diem']} ({e(p['hang'])})</td></tr>" for p in ds)
    return f"<table><thead><tr><th>Program</th><th>Commission</th><th>Cookie</th><th>ClickScore</th></tr></thead><tbody>{r}</tbody></table>"


def doan_ct(p, so=None):
    """Một đoạn mô tả chương trình dùng trong bài 'best of'."""
    dau = f"{so}. " if so else ""
    tan = p["payout"].get("frequency")
    cau_tan = f" Payouts are {e(tan.replace('-', ' '))}" + (f" with a ${p['payout']['minimum']} minimum." if isinstance(p['payout'].get('minimum'), (int, float)) else ".") if tan else ""
    duyet = {"auto": " Approval is automatic, so you can start the same day.", "manual": " Applications are reviewed manually" + (f" ({e(p['approval_time'])})." if p['approval_time'] else "."),
             "invite-only": " The program is invite-only."}.get(p["approval"], "")
    ck = f" The cookie lasts {int(p['cookie'])} days." if p["cookie"] else " The cookie window is not published."
    hop = f" Best for: {e(giua_cau(p['use_cases'][0].rstrip('.')))}." if p["use_cases"] else ""
    return (f"<h3>{dau}<a href=\"{u('programs/' + p['slug'] + '/')}\">{e(p['name'])}</a> — {e(p['nhan'])}</h3>"
            f"<p>{e(p['ngan'])} {chon(p['slug'], 'The program pays', 'Partners earn', 'Affiliates receive')} <b>{e(p['nhan'])}</b>.{ck}{cau_tan}{duyet}{hop} "
            f"ClickScore: <b>{p['diem']}/100 ({e(p['hang'])})</b>.</p>")


def faq_html(faq):
    return "<h2>FAQ</h2>" + "".join(f"<h3>{e(q)}</h3><p>{a}</p>" for q, a in faq)


def bai_best(cat, ds_cat, thang):
    ten_thang = thang.strftime("%B %Y")
    top = ds_cat[:10]
    n = len(top)
    tieu = f"{n} Best {cat} Affiliate Programs ({ten_thang})"
    rec = [p for p in ds_cat if p["c"]["type"] == "recurring"]
    rec_khac = [p for p in rec if p is not top[0]]
    mo = (f"<p>{chon(cat + ten_thang, 'Looking for', 'Want to promote', 'Building a site around')} {e(thuong(cat))} tools? "
          f"We track <b>{len(ds_cat)}</b> {e(cat)} affiliate programs and rank them every day by ClickScore — a 100-point score built from commission, cookie window, "
          f"verification and payout terms. These are the {n} that score highest this month.</p>")
    tom = (f"<div class=\"note\"><b>Quick picks:</b> best overall — <a href=\"{u('programs/' + top[0]['slug'] + '/')}\">{e(top[0]['name'])}</a> ({e(top[0]['nhan'])})"
           + (f"; runner-up recurring — <a href=\"{u('programs/' + rec_khac[0]['slug'] + '/')}\">{e(rec_khac[0]['name'])}</a> ({e(rec_khac[0]['nhan'])})" if rec_khac else "")
           + (f"; longest cookie — {e(max(top, key=lambda x: x['cookie'] or 0)['name'])} ({int(max(top, key=lambda x: x['cookie'] or 0)['cookie'] or 0)} days)" if any(p['cookie'] for p in top) else "")
           + ".</div>")
    than = (mo + tom + "<h2>At a glance</h2>" + bang_so_lieu(top) + "<h2>The programs</h2>"
            + "".join(doan_ct(p, i) for i, p in enumerate(top, 1))
            + f"<h2>How we picked</h2><p>Every program in this list comes from our daily-updated directory. Programs whose terms were checked against the brand's own affiliate page are marked verified and score higher. "
              f"See <a href=\"{u('about/')}#clickscore\">how ClickScore works</a> or browse <a href=\"{u('categories/' + slugify(cat) + '/')}\">all {e(cat)} programs</a>.</p>")
    faq = [(f"What is the best {cat} affiliate program?", f"Right now {e(top[0]['name'])} ranks first with a ClickScore of {top[0]['diem']}, paying {e(top[0]['nhan'])}."),
           (f"Do {cat} affiliate programs pay recurring commission?", f"{len(rec)} of the {len(ds_cat)} {e(cat)} programs we track pay recurring commission" + (f", led by {e(rec[0]['name'])}." if rec else ".")),
           ("How often is this list updated?", "The ranking behind this article is recalculated every day as program terms change.")]
    mota = f"The {n} best {cat} affiliate programs for {ten_thang}, ranked by commission, cookie length and payout terms. Updated daily."
    return tieu, mota, than + faq_html(faq), faq


def bai_review(p, ds_cat):
    tieu = f"{p['name']} Affiliate Program Review: Commission, Cookie & Payout"
    hang_dm = ds_cat.index(p) + 1 if p in ds_cat else None
    tan = p["payout"]
    pp = ", ".join(tan.get("methods") or []) or "not published"
    dong = [("Commission", e(p["nhan"])), ("Cookie window", f"{int(p['cookie'])} days" if p["cookie"] else "Not published"),
            ("Payout schedule", e((tan.get("frequency") or "Not published").replace("-", " "))),
            ("Minimum payout", f"${tan['minimum']}" if isinstance(tan.get("minimum"), (int, float)) else "Not published"),
            ("Payout methods", e(pp)), ("Approval", e(p["approval"] or "Not published") + (f" ({e(p['approval_time'])})" if p["approval_time"] else "")),
            ("Network", e(p["network"] or "—")), ("Verified", "Yes" + (f", {p['last_verified']:%b %-d, %Y}" if p["last_verified"] else "") if p["verified"] else "Not yet")]
    bang = "<table><tbody>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in dong) + "</tbody></table>"
    tot, xau = [], []
    if p["c"]["type"] == "recurring":
        tot.append("Recurring commission — you keep earning while referrals stay subscribed")
    if (p["cookie"] or 0) >= 60:
        tot.append(f"Long {int(p['cookie'])}-day cookie")
    if p["approval"] in ("auto", "automatic"):
        tot.append("Instant approval")
    if p["verified"]:
        tot.append("Terms verified against the brand's own page")
    if p["materials"]:
        tot.append("Marketing materials provided")
    if not p["cookie"]:
        xau.append("Cookie length not published")
    elif p["cookie"] < 30:
        xau.append(f"Short {int(p['cookie'])}-day cookie")
    if p["c"]["type"] == "one-time":
        xau.append("One-time payout only")
    if p["approval"] == "manual":
        xau.append("Manual approval")
    if len(p["restrictions"]) > 2:
        xau.append(f"{len(p['restrictions'])} promotion restrictions to follow")
    if not p["verified"]:
        xau.append("Community-submitted terms, not yet verified")
    ul = lambda xs: "<ul>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>" if xs else "<p>None stand out.</p>"
    rs = ("<h2>Rules to know before you apply</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in p["restrictions"][:8]) + "</ul>") if p["restrictions"] else ""
    ket = chon(p["slug"], "Verdict", "Bottom line", "Should you join?")
    than = (f"<p>{e(p['desc'].split('Affiliate program:')[0].strip())}</p>"
            f"<p>This review covers the terms of the {e(p['name'])} affiliate program and how it compares with the "
            f"{len(ds_cat)} other {e(p['cat'])} programs we track. It currently has a <b>ClickScore of {p['diem']}/100 ({e(p['hang'])})</b>"
            + (f", ranking <b>#{hang_dm}</b> in {e(p['cat'])}." if hang_dm else ".") + "</p>"
            f"<h2>Key terms</h2>{bang}"
            + (f"<p><b>Commission details:</b> {e(p['c']['conditions'])}</p>" if p["c"]["conditions"] else "")
            + f"<h2>Pros</h2>{ul(tot)}<h2>Cons</h2>{ul(xau)}{rs}"
            f"<h2>{ket}</h2><p>{e(p['name'])} is "
            + ("one of the stronger programs" if p["diem"] >= 78 else "a solid option" if p["diem"] >= 62 else "a niche pick")
            + f" for creators who write about {e(thuong(p['cat']))}. "
            + (f"Its best fit: {e(giua_cau(p['use_cases'][0].rstrip('.')))}. " if p["use_cases"] else "")
            + f"Always confirm the current terms on the <a href=\"{e(p['signup'])}\" rel=\"nofollow sponsored noopener\" target=\"_blank\">official affiliate page</a> before you promote.</p>"
            + f"<p>Compare it with <a href=\"{u('categories/' + p['cat_slug'] + '/')}\">other {e(p['cat'])} affiliate programs</a>.</p>")
    faq = [(f"How much does the {p['name']} affiliate program pay?", f"{e(p['name'])} pays {e(giua_cau(p['nhan']))}."),
           (f"How long is the {p['name']} affiliate cookie?", f"{int(p['cookie'])} days." if p["cookie"] else "The cookie window is not published."),
           (f"How do I join the {p['name']} affiliate program?", "Apply on the official affiliate page" + (f" via {e(p['network'])}" if p["network"] and p["network"] != "in-house" else "") + ". Approval is " + e(p["approval"] or "not specified") + ".")]
    mota = f"{p['name']} affiliate program review: {p['nhan']}, " + (f"{int(p['cookie'])}-day cookie" if p["cookie"] else "cookie terms") + f", payout details, pros and cons. ClickScore {p['diem']}/100."
    return tieu, mota, than + faq_html(faq), faq


def bai_vs(a, b):
    tieu = f"{a['name']} vs {b['name']} Affiliate Program: Which Pays More?"
    dong = [("Commission", a["nhan"], b["nhan"]), ("Cookie", f"{int(a['cookie'])} days" if a["cookie"] else "—", f"{int(b['cookie'])} days" if b["cookie"] else "—"),
            ("Payout", (a["payout"].get("frequency") or "—"), (b["payout"].get("frequency") or "—")),
            ("Approval", a["approval"] or "—", b["approval"] or "—"), ("Verified", "Yes" if a["verified"] else "No", "Yes" if b["verified"] else "No"),
            ("ClickScore", f"{a['diem']} ({a['hang']})", f"{b['diem']} ({b['hang']})")]
    bang = f"<table><thead><tr><th></th><th>{e(a['name'])}</th><th>{e(b['name'])}</th></tr></thead><tbody>" + "".join(
        f"<tr><th>{k}</th><td>{e(x)}</td><td>{e(y)}</td></tr>" for k, x, y in dong) + "</tbody></table>"
    thang = a if a["diem"] >= b["diem"] else b
    thua = b if thang is a else a
    than = (f"<p>{e(a['name'])} and {e(b['name'])} are two of the highest-ranked {e(a['cat'])} affiliate programs in our directory. "
            f"If you can only promote one, here is how their terms compare side by side.</p><h2>Side-by-side</h2>{bang}"
            f"<h2>{e(a['name'])}</h2><p>{e(a['ngan'])}</p><h2>{e(b['name'])}</h2><p>{e(b['ngan'])}</p>"
            f"<h2>Which one should you promote?</h2><p>On terms alone, <b>{e(thang['name'])}</b> comes out ahead with a ClickScore of {thang['diem']} "
            f"versus {thua['diem']}. But the best program is the one your audience actually needs: pick {e(a['name'])} if your readers want "
            f"{e(a['ngan'][:90].lower().rstrip('.'))}…, and {e(b['name'])} if they want {e(b['ngan'][:90].lower().rstrip('.'))}…. Many affiliates promote both.</p>"
            f"<p>Read the full reviews: <a href=\"{u('programs/' + a['slug'] + '/')}\">{e(a['name'])}</a> · <a href=\"{u('programs/' + b['slug'] + '/')}\">{e(b['name'])}</a>.</p>")
    faq = [(f"Does {a['name']} or {b['name']} pay more?", f"{e(a['name'])} pays {e(giua_cau(a['nhan']))}; {e(b['name'])} pays {e(giua_cau(b['nhan']))}."),
           (f"Which has the longer cookie?", f"{e(a['name'])}: {e(dong[1][1])}. {e(b['name'])}: {e(dong[1][2])}.")]
    mota = f"{a['name']} vs {b['name']} affiliate programs compared: commission ({a['nhan']} vs {b['nhan']}), cookie, payout and approval."
    return tieu, mota, than + faq_html(faq), faq


def bai_tuan(moi, tuan_ngay):
    tieu = f"New Affiliate Programs This Week ({tuan_ngay:%B %-d, %Y})"
    moi = sorted(moi, key=lambda p: -p["diem"])
    than = (f"<p>{len(moi)} affiliate programs joined our directory in the past seven days. Here they are, best-scoring first.</p>"
            + bang_so_lieu(moi[:25]) + "<h2>Highlights</h2>" + "".join(doan_ct(p) for p in moi[:6])
            + f"<p>See every newly added program on the <a href=\"{u('new/')}\">New programs</a> page.</p>")
    faq = [("How often are new affiliate programs added?", "Our directory syncs every day; this roundup is published weekly.")]
    mota = f"{len(moi)} new affiliate programs added this week, with commission, cookie and ClickScore for each."
    return tieu, mota, than + faq_html(faq), faq


HUONG_DAN = [  # bài viết tay, cố định
    ("what-is-affiliate-marketing", "What Is Affiliate Marketing? A Plain-English Guide",
     "Affiliate marketing explained: how commissions, cookies and payouts work, and how to pick programs worth promoting.",
     """<p>Affiliate marketing is a simple deal: a company pays you a commission when someone you refer buys its product. You share a tracked link; the company's software records the visit, and if a sale happens within the <b>cookie window</b>, the sale is credited to you.</p>
<h2>The four terms that decide what you earn</h2>
<ul><li><b>Commission</b> — a percentage of the sale (for example 30%) or a flat amount (for example $100 per signup).</li>
<li><b>Recurring vs one-time</b> — recurring programs keep paying every month the customer stays subscribed, sometimes for life. For software, recurring is usually worth far more.</li>
<li><b>Cookie window</b> — how long after the click you still get credit. 30 days is common; 90+ days is generous.</li>
<li><b>Payout terms</b> — how often you are paid, the minimum balance, and the methods (PayPal, bank, Stripe).</li></ul>
<h2>How to choose a program</h2>
<p>Start with what your audience already needs, then compare programs in that niche on the four terms above. That is exactly what our <a href="{P}/rankings/">daily rankings</a> do for you.</p>
<h2>Rules to respect</h2><p>Most programs forbid bidding on their brand name in ads, self-referrals and coupon-site promotion. Always disclose affiliate links to your readers — it is required by law in many countries.</p>"""),
    ("recurring-vs-one-time-commission", "Recurring vs One-Time Affiliate Commission: Which Earns More?",
     "Why recurring affiliate commissions usually beat one-time payouts for SaaS, with simple math.",
     """<p>A one-time commission pays you once per sale. A recurring commission pays you every billing cycle the customer stays — for 12 months, 24 months or the lifetime of the account.</p>
<h2>The math</h2><p>A tool costs $30/month. Program A pays a one-time $50. Program B pays 30% recurring for 12 months: $9 × 12 = <b>$108</b> per customer if they stay a year. With lifetime terms and a two-year average customer, it becomes $216.</p>
<h2>When one-time is better</h2><p>For products with high churn, annual plans paid up front, or high-ticket flat bounties ($100–$500 per signup), a one-time payout can win. Compare the numbers, not the label.</p>
<p>Filter our <a href="{P}/programs/">directory</a> by commission type to see the best recurring programs today.</p>"""),
    ("how-to-start-affiliate-marketing", "How to Start Affiliate Marketing in 2026 (Step by Step)",
     "A practical step-by-step plan to start affiliate marketing: niche, content, programs, links and tracking.",
     """<h2>1. Pick a niche you can write about weekly</h2><p>Choose a topic where people buy tools: AI, marketing, design, productivity, finance. Our <a href="{P}/categories/">categories</a> show how many programs each niche has.</p>
<h2>2. Choose 3–5 programs</h2><p>Use the <a href="{P}/rankings/">rankings</a> to shortlist programs with recurring commission, a cookie of 60+ days and verified terms.</p>
<h2>3. Create content that answers buying questions</h2><p>Reviews, comparisons ("X vs Y"), tutorials and "best tools for…" lists convert best because the reader is already deciding.</p>
<h2>4. Disclose and track</h2><p>Add a clear affiliate disclosure, use each program's dashboard to track clicks, and double down on the pages that earn.</p>
<h2>5. Review your programs every month</h2><p>Terms change. Programs get paused. We re-check and re-rank every day so you can see when a program you promote drops.</p>"""),
]


# ───────────────────────── dựng trang ─────────────────────────

def dung(nguon, ra, so_dang):
    ds = doc_chuong_trinh(nguon)
    xep = sorted([p for p in ds if p["status"] not in KHONG_XEP], key=lambda p: (-p["diem"], not p["verified"], p["name"].lower()))
    for i, p in enumerate(xep, 1):
        p["hang_so"] = i

    # sổ trạng thái: ngày thấy lần đầu + lịch sử thứ hạng
    sd = os.path.join(GOC, "state")
    seen = doc_json(os.path.join(sd, "seen.json"), {})
    lan_dau = not seen
    for p in ds:
        if p["slug"] not in seen:
            seen[p["slug"]] = (p["created"] or HOM_NAY).isoformat() if lan_dau else HOM_NAY.isoformat()
        p["seen"] = dt.date.fromisoformat(seen[p["slug"]])
    ls = doc_json(os.path.join(sd, "rank_history.json"), {})
    ls[HOM_NAY.isoformat()] = {p["slug"]: p["hang_so"] for p in xep[:300]}
    ngay_cu = sorted(d for d in ls if d < HOM_NAY.isoformat())
    hom_qua = ls[ngay_cu[-1]] if ngay_cu else {}
    ls = {d: ls[d] for d in sorted(ls)[-30:]}
    di_chuyen = {p["slug"]: (hom_qua[p["slug"]] - p["hang_so"]) for p in xep if p["slug"] in hom_qua} if hom_qua else {p["slug"]: 0 for p in xep}

    theo_dm = {}
    for p in xep:
        theo_dm.setdefault(p["cat"], []).append(p)
    dms = sorted(theo_dm.items(), key=lambda kv: -len(kv[1]))
    moi = sorted(ds, key=lambda p: (p["seen"], p["diem"]), reverse=True)
    moi_tuan = [p for p in ds if (HOM_NAY - p["seen"]).days < 7]

    # ── bài blog: kế hoạch đăng ──
    posts = doc_json(os.path.join(sd, "posts.json"), [])
    da = {b["key"] for b in posts}
    def dang(key, kieu, slug, **x):
        posts.append({"key": key, "type": kieu, "slug": slug, "date": HOM_NAY.isoformat(), **x}); da.add(key)
    so_bai = so_dang * (4 if lan_dau else 1)
    for s, *_ in HUONG_DAN:
        if f"guide-{s}" not in da:
            dang(f"guide-{s}", "guide", s)
    con = so_bai
    tuan = HOM_NAY.isocalendar()
    k_tuan = f"week-{tuan[0]}-{tuan[1]}"
    if k_tuan not in da and len(moi_tuan) >= 3 and con > 0:
        dang(k_tuan, "week", f"new-affiliate-programs-week-{tuan[1]}-{tuan[0]}"); con -= 1
    thang = HOM_NAY.strftime("%Y-%m")
    loai = 0
    while con > 0:
        tien = False
        if loai % 3 == 0:   # best-of theo danh mục
            for cat, l in dms:
                k = f"best-{slugify(cat)}-{thang}"
                if k not in da and len(l) >= 5:
                    dang(k, "best", f"best-{slugify(cat)}-affiliate-programs-{HOM_NAY:%B-%Y}".lower(), cat=cat, thang=thang); tien = True; break
        elif loai % 3 == 1:  # review chương trình điểm cao chưa viết
            for p in xep:
                k = f"review-{p['slug']}"
                if k not in da and p["verified"]:
                    dang(k, "review", f"{p['slug']}-affiliate-program-review", prog=p["slug"]); tien = True; break
        else:                # so sánh hai chương trình cùng danh mục — rải đều, ít lặp tên
            dung_vs = {}
            for b in posts:
                if b["type"] == "vs":
                    for x in (b["a"], b["b"], "cat:" + b.get("cat", "")):
                        dung_vs[x] = dung_vs.get(x, 0) + 1
            ung = []
            for cat, l in dms:
                top = l[:6]
                for i in range(len(top)):
                    for j in range(i + 1, len(top)):
                        a, b2 = top[i], top[j]
                        if f"vs-{a['slug']}-{b2['slug']}" not in da:
                            ung.append((dung_vs.get(a["slug"], 0) + dung_vs.get(b2["slug"], 0) + dung_vs.get("cat:" + cat, 0), i + j, cat, a, b2))
            if ung:
                _, _, cat, a, b2 = min(ung, key=lambda x: x[:2])
                dang(f"vs-{a['slug']}-{b2['slug']}", "vs", f"{a['slug']}-vs-{b2['slug']}-affiliate-program", a=a["slug"], b=b2["slug"], cat=cat); tien = True
        con -= 1 if tien else 0
        loai += 1
        if loai > so_bai * 6 + 9:
            break

    for b in noi_dung_vi.BAI_VI:
        if f"vi-{b['slug']}" not in da:
            dang(f"vi-{b['slug']}", "vi", b["slug"])

    # ── dựng nội dung từng bài từ dữ liệu hôm nay ──
    theo_slug = {p["slug"]: p for p in ds}
    bai = []
    for b in posts:
        r = None
        if b["type"] == "guide":
            g = next((g for g in HUONG_DAN if g[0] == b["slug"]), None)
            if g:
                r = (g[1], g[2], g[3].replace("{P}", P), [])
        elif b["type"] == "best" and b["cat"] in theo_dm:
            r = bai_best(b["cat"], theo_dm[b["cat"]], dt.date.fromisoformat(b["thang"] + "-01"))
        elif b["type"] == "review" and b["prog"] in theo_slug:
            p = theo_slug[b["prog"]]
            r = bai_review(p, theo_dm.get(p["cat"], []))
        elif b["type"] == "vs" and b["a"] in theo_slug and b["b"] in theo_slug:
            r = bai_vs(theo_slug[b["a"]], theo_slug[b["b"]])
        elif b["type"] == "week":
            d0 = dt.date.fromisoformat(b["date"])
            m = [p for p in ds if 0 <= (d0 - p["seen"]).days < 7]
            if m:
                r = bai_tuan(m, d0)
        if r:
            bai.append({**b, "tieu": r[0], "mota": r[1], "than": r[2], "faq": r[3]})
    bai.sort(key=lambda b: (b["date"], b["key"]), reverse=True)

    # ── ghi ra ──
    if os.path.isdir(ra):
        shutil.rmtree(ra)
    os.makedirs(ra)
    shutil.copytree(os.path.join(GOC, "assets"), os.path.join(ra, "assets"))
    so_ver = sum(p["verified"] for p in ds)
    org = {"@context": "https://schema.org", "@type": "Organization", "name": TEN, "url": SITE_URL + "/", "logo": f"{SITE_URL}/assets/icon-512.png"}

    # trang chủ
    def bai_item(b):
        nhan = {"best": "Best of", "review": "Review", "vs": "Comparison", "week": "New this week", "guide": "Guide"}[b["type"]]
        return (f'<a class="card bai-item" href="{u("blog/" + b["slug"] + "/")}"><div class="meta"><span class="pill xanh">{nhan}</span>'
                f'{dt.date.fromisoformat(b["date"]):%b %-d, %Y}</div><h3>{e(b["tieu"])}</h3><p>{e(b["mota"])}</p></a>')
    ver_top = [p for p in xep if p["verified"]][:6]
    dm_html = "".join(f'<a class="card" href="{u("categories/" + slugify(c) + "/")}">{e(c)}<small>{len(l)}</small></a>' for c, l in dms)
    than = f"""<div class="wrap">
<section class="hero"><span class="pill xanh">Updated daily · {HOM_NAY:%B %-d, %Y}</span>
<h1>Find affiliate programs <em>worth promoting</em>.</h1>
<p class="lead">{TEN} tracks {len(ds):,} affiliate programs, scores every one on commission, cookie, payout and approval, and re-ranks them every day. No paid placements.</p>
<div class="cta"><a class="btn chinh" href="{u('rankings/')}">See today's top programs →</a><a class="btn" href="{u('programs/')}">Browse the directory</a></div>
<div class="stats"><div class="card stat"><b>{len(ds):,}</b><small>Programs tracked</small></div><div class="card stat"><b>{so_ver:,}</b><small>Terms verified</small></div>
<div class="card stat"><b>{len(moi_tuan):,}</b><small>New this week</small></div><div class="card stat"><b>$0</b><small>Paid placement</small></div></div></section>
<section class="khoi"><div class="khoi-dau"><div><h2>Today's top 10</h2><p>Ranked by ClickScore. Arrows show movement since yesterday.</p></div><a href="{u('rankings/')}">Full rankings →</a></div>
{bang_xep(xep[:10], di_chuyen=di_chuyen)}</section>
<section class="khoi"><div class="khoi-dau"><div><h2>Top verified programs</h2><p>Terms checked against the brand's own affiliate page.</p></div><a href="{u('programs/')}">All programs →</a></div>
<div class="luoi">{''.join(the_ct(p) for p in ver_top)}</div></section>
<section class="khoi"><div class="khoi-dau"><div><h2>Just added</h2><p>The newest programs in the directory.</p></div><a href="{u('new/')}">All new →</a></div>
<div class="luoi">{''.join(the_ct(p, f'<span class="pill vang">added {p["seen"]:%b %-d}</span>') for p in moi[:6])}</div></section>
<section class="khoi"><div class="khoi-dau"><div><h2>Categories</h2><p>{len(dms)} niches, ranked inside each one.</p></div></div><div class="danh-muc">{dm_html}</div></section>
<section class="khoi"><a class="card vi-dai" href="{u('vi/')}"><span class="pill xanh">🌐 Tiếng Việt</span><b>Làm Affiliate và đang tìm sản phẩm ngon?</b><span>Đọc bài hướng dẫn bằng tiếng Việt →</span></a></section>
<section class="khoi">{hop_dk("home")}</section>
<section class="khoi"><div class="khoi-dau"><div><h2>From the blog</h2><p>New guides, reviews and comparisons every day.</p></div><a href="{u('blog/')}">All articles →</a></div>
<div class="bai-list">{''.join(bai_item(b) for b in bai[:5])}</div></section>
</div>"""
    web = {"@context": "https://schema.org", "@type": "WebSite", "name": TEN, "url": SITE_URL + "/",
           "potentialAction": {"@type": "SearchAction", "target": f"{SITE_URL}/programs/?q={{q}}", "query-input": "required name=q"}}
    bo_dl = {"@context": "https://schema.org", "@type": "Dataset", "name": f"{TEN} affiliate program rankings",
             "description": f"Daily ClickScore rankings of {len(ds)} affiliate programs: commission, cookie, payout, approval.",
             "url": SITE_URL + "/", "dateModified": HOM_NAY.isoformat(), "license": "https://opensource.org/licenses/MIT", "creator": org,
             "isBasedOn": NGUON_DL, "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE_URL}/data/programs.json"},
                                                     {"@type": "DataDownload", "encodingFormat": "text/markdown", "contentUrl": f"{SITE_URL}/llms-full.txt"}]}
    ghi(ra, "", khung(f"{TEN} — Best Affiliate Programs, Ranked Daily", f"Compare {len(ds):,} affiliate programs by commission, cookie length and payout. Ranked every day by ClickScore. No paid placements.", "", than, ld=[web, org, bo_dl]))

    # xếp hạng
    top = xep[:100]
    il = {"@context": "https://schema.org", "@type": "ItemList", "name": "Top affiliate programs", "itemListElement": [
        {"@type": "ListItem", "position": i, "url": f"{SITE_URL}/programs/{p['slug']}/", "name": p["name"]} for i, p in enumerate(top[:50], 1)]}
    than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><span class="pill xanh">Re-ranked {HOM_NAY:%B %-d, %Y}</span>
<h1>Top 100 affiliate programs</h1><p class="lead">Every program scored out of 100 on commission, cookie window, trust and terms. <a href="{u('about/')}#clickscore">How ClickScore works</a>.</p></section>
{bang_xep(top, di_chuyen=di_chuyen)}</div>"""
    ghi(ra, "rankings", khung(f"Top 100 Affiliate Programs ({HOM_NAY:%B %Y}) — Ranked Daily", "The 100 best affiliate programs today, ranked by commission, cookie length, payout and verified terms. Updated every day.", "rankings/", than, ld=[il], nav="rankings/"))

    # thư mục + dữ liệu cho bộ lọc
    nhe = [{"s": p["slug"], "n": p["name"], "d": p["ngan"], "c": p["cat"], "cs": p["cat_slug"], "r": p["nhan"], "t": p["c"]["type"],
            "v": p["c"]["value"] or 0, "k": p["cookie"] or 0, "sc": p["diem"], "g": p["hang"], "ok": p["verified"], "dm": p["domain"],
            "a": p["seen"].isoformat(), "x": p["status"] in KHONG_XEP} for p in sorted(ds, key=lambda p: -p["diem"])]
    os.makedirs(os.path.join(ra, "data"), exist_ok=True)
    with open(os.path.join(ra, "data", "programs.json"), "w", encoding="utf-8") as f:
        json.dump(nhe, f, ensure_ascii=False, separators=(",", ":"))
    opt = "".join(f'<option value="{e(c)}">{e(c)} ({len(l)})</option>' for c, l in dms)
    than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><h1>Affiliate program directory</h1>
<p class="lead">Search and filter all {len(ds):,} programs. Sort by score, commission, cookie or newest.</p></section>
<div class="card loc"><input type="search" id="q" placeholder="Search programs, e.g. AI writing, CRM, hosting…" autocomplete="off">
<select id="cat"><option value="">All categories</option>{opt}</select>
<select id="typ"><option value="">Any commission</option><option value="recurring">Recurring</option><option value="one-time">One-time</option><option value="hybrid">Hybrid / tiered</option></select>
<select id="sort"><option value="sc">Sort: ClickScore</option><option value="v">Sort: commission %</option><option value="k">Sort: cookie length</option><option value="a">Sort: newest</option><option value="n">Sort: A–Z</option></select>
<label><input type="checkbox" id="ver"> Verified only</label></div>
<p class="dem" id="dem"></p><div id="ds">{bang_xep(xep[:50])}</div>
<div style="text-align:center;margin-top:14px"><button class="btn" id="them" hidden>Show more</button></div></div>
<script>window.CA_BASE={json.dumps(P)};</script><script src="{u('assets/app.js')}?v={HOM_NAY.isoformat()}" defer></script>"""
    ghi(ra, "programs", khung("Affiliate Program Directory — Search & Compare", f"Search {len(ds):,} affiliate programs. Filter by category, recurring commission, cookie length and verified terms.", "programs/", than, nav="programs/"))

    # trang từng chương trình
    bai_ve = {b["prog"]: b for b in bai if b["type"] == "review"}
    for p in ds:
        cung = [x for x in theo_dm.get(p["cat"], []) if x["slug"] != p["slug"]][:6]
        tan = p["payout"]
        chia = "".join(f'<div class="dong"><span>{k}</span><div class="thanh"><span style="width:{round(v / m * 100)}%"></span></div><b>{v}/{m}</b></div>' for k, v, m in p["chia"])
        rs = ("<h2>Restrictions</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in p["restrictions"][:10]) + "</ul>") if p["restrictions"] else ""
        hang_txt = (f"#{p['hang_so']} overall · #{theo_dm[p['cat']].index(p) + 1} in {e(p['cat'])}" if p.get("hang_so") else "Not ranked (program paused)")
        faq = [(f"How much does {p['name']} pay affiliates?", f"{e(p['name'])} pays {e(giua_cau(p['nhan']))}."),
               (f"What is the {p['name']} affiliate cookie duration?", f"{int(p['cookie'])} days." if p["cookie"] else "Not published by the program."),
               (f"Is the {p['name']} affiliate program legit?", ("Yes — its terms were verified against the official program page" + (f" on {p['last_verified']:%B %-d, %Y}" if p["last_verified"] else "") + ".") if p["verified"] else "Its terms are community-submitted and not yet verified. Check the official page before applying.")]
        ld = [vun(("Home", ""), ("Programs", "programs/"), (p["name"], f"programs/{p['slug']}/")),
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in faq]}]
        rv = bai_ve.get(p["slug"])
        tra_loi = (f"The {e(p['name'])} affiliate program pays <b>{e(giua_cau(p['nhan']))}</b>"
                   + (f" with a {int(p['cookie'])}-day cookie" if p["cookie"] else "")
                   + (f", {e(tan['frequency'].replace('-', ' '))} payouts" if tan.get("frequency") else "")
                   + (f" and {e(p['approval'])} approval" if p["approval"] else "") + ". "
                   + f"ClickScore {p['diem']}/100 ({e(p['hang'])}) — {hang_txt}."
                   + (f" Terms verified {p['last_verified']:%B %-d, %Y}." if p["verified"] and p["last_verified"] else " Terms not yet verified."))
        than = f"""<div class="wrap"><div class="doc" style="max-width:900px">
<div class="crumb"><a href="{u()}">Home</a> / <a href="{u('programs/')}">Programs</a> / <a href="{u('categories/' + p['cat_slug'] + '/')}">{e(p['cat'])}</a></div>
<div class="ct-dau">{logo_ct(p, 60)}<div><h1>{e(p['name'])} affiliate program</h1><div class="meta">{diem_html(p)}<span>{hang_txt}</span>
{'<span class="pill ok">✓ verified' + (f" {p['last_verified']:%b %-d, %Y}" if p['last_verified'] else '') + '</span>' if p['verified'] else '<span class="pill vang">unverified</span>'}
{'<span class="pill do">paused</span>' if p['status'] in KHONG_XEP else ''}</div></div></div>
<div class="note"><b>Quick answer:</b> {tra_loi}</div>
<p>{e(p['desc'])}</p>
<div class="so-lieu"><div class="card"><small>Commission</small><b>{e(p['c']['rate'] or 'Varies')}</b><span class="meta">{e(p['c']['type'])}{(' · ' + e(p['c']['duration'])) if p['c']['duration'] else ''}</span></div>
<div class="card"><small>Cookie</small><b>{f"{int(p['cookie'])} days" if p['cookie'] else '—'}</b><span class="meta">{e(p['attribution'] or '')}</span></div>
<div class="card"><small>Payout</small><b>{e((tan.get('frequency') or '—').replace('-', ' '))}</b><span class="meta">{('min $' + str(tan['minimum'])) if isinstance(tan.get('minimum'), (int, float)) else ''}</span></div>
<div class="card"><small>Approval</small><b>{e(p['approval'] or '—')}</b><span class="meta">{e(p['network'])}</span></div></div>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 10px"><a class="btn chinh" href="{e(p['signup'])}" rel="nofollow sponsored noopener" target="_blank">Apply to the program ↗</a>
{f'<a class="btn chinh" href="{e(LINK_AFF[p["slug"]])}" rel="nofollow sponsored noopener" target="_blank">Try {e(p["name"])} ↗</a>' if p['slug'] in LINK_AFF else (f'<a class="btn" href="{e(p["url"])}" rel="nofollow noopener" target="_blank">Visit {e(p["domain"])} ↗</a>' if p['url'] else '')}
{f'<a class="btn" href="{u("blog/" + rv["slug"] + "/")}">Read our review</a>' if rv else ''}</div>
{f"<p><b>Commission details:</b> {e(p['c']['conditions'])}</p>" if p['c']['conditions'] else ''}
<h2>ClickScore breakdown</h2><div class="card diem-chia">{chia}</div>
{rs}
{('<h2>Who it suits</h2><ul>' + ''.join(f'<li>{e(x)}</li>' for x in p['use_cases']) + '</ul>') if p['use_cases'] else ''}
{faq_html(faq)}
<h2>Similar {e(p['cat'])} programs</h2></div><div class="luoi">{''.join(the_ct(x) for x in cung)}</div>
<div style="margin-top:20px">{hop_dk("program:" + p["slug"], tieu=f"Get alerts on {e(p['cat'])} programs", mo=f"New {e(p['cat'])} affiliate programs and term changes, once a week. Free.")}</div>
<p class="note vang" style="margin-top:20px">Terms change. Always confirm commission and rules on the official affiliate page before promoting.</p></div>"""
        mota = f"{p['name']} affiliate program: {p['nhan']}" + (f", {int(p['cookie'])}-day cookie" if p["cookie"] else "") + f". ClickScore {p['diem']}/100. Payout, approval and rules."
        ghi(ra, f"programs/{p['slug']}", khung(f"{p['name']} Affiliate Program — {p['nhan']}", mota, f"programs/{p['slug']}/", than, ld=ld, nav="programs/", md=True))
        ghi(ra, f"programs/{p['slug']}/index.md", f"# {p['name']} affiliate program\n\n> {sang_md(tra_loi).strip()}\n\n"
            + f"- Commission: {p['nhan']}\n- Cookie: {str(int(p['cookie'])) + ' days' if p['cookie'] else 'not published'}\n"
            + f"- Payout: {tan.get('frequency') or 'not published'}" + (f", minimum ${tan['minimum']}" if isinstance(tan.get('minimum'), (int, float)) else "") + "\n"
            + f"- Approval: {p['approval'] or 'not published'}\n- Network: {p['network'] or '-'}\n- Category: {p['cat']}\n- Verified: {'yes, ' + str(p['last_verified']) if p['verified'] else 'no'}\n"
            + f"- ClickScore: {p['diem']}/100 ({p['hang']}); " + ", ".join(f"{k} {v}/{m}" for k, v, m in p['chia']) + "\n"
            + f"- Apply: {p['signup']}\n- Website: {p['url']}\n\n{p['desc']}\n\n"
            + (("## Restrictions\n\n" + "".join(f"- {x}\n" for x in p['restrictions'][:10]) + "\n") if p['restrictions'] else "")
            + f"Source page: {SITE_URL}/programs/{p['slug']}/ · Updated {HOM_NAY}\n")

    # danh mục
    than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><h1>Affiliate programs by category</h1><p class="lead">{len(dms)} niches. Each one ranked by ClickScore.</p></section>
<div class="danh-muc">{dm_html}</div></div>"""
    ghi(ra, "categories", khung("Affiliate Program Categories", "Browse affiliate programs by niche: AI, marketing, design, finance, e-commerce and more — ranked daily.", "categories/", than, nav="categories/"))
    for cat, l in dms:
        cs = slugify(cat)
        bb = next((b for b in bai if b["type"] == "best" and b["cat"] == cat), None)
        than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><div class="crumb"><a href="{u('categories/')}">Categories</a> / {e(cat)}</div>
<h1>Best {e(cat)} affiliate programs</h1><p class="lead">{len(l)} {e(cat)} programs, ranked by ClickScore. Updated {HOM_NAY:%B %-d, %Y}.</p>
{f'<a class="btn" href="{u("blog/" + bb["slug"] + "/")}">Read: {e(bb["tieu"])}</a>' if bb else ''}</section>
{bang_xep(l, co_dm=False)}</div>"""
        ld = [vun(("Home", ""), ("Categories", "categories/"), (cat, f"categories/{cs}/")),
              {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{SITE_URL}/programs/{p['slug']}/"} for i, p in enumerate(l[:30], 1)]}]
        ghi(ra, f"categories/{cs}", khung(f"Best {cat} Affiliate Programs ({HOM_NAY:%Y}) — {len(l)} Ranked", f"The best {cat} affiliate programs ranked by commission, cookie and payout. {len(l)} programs, updated daily.", f"categories/{cs}/", than, ld=ld, nav="categories/"))

    # mới
    than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><h1>New affiliate programs</h1><p class="lead">The latest programs added to the directory. {len(moi_tuan)} this week.</p></section>
<div class="luoi">{''.join(the_ct(p, f'<span class="pill vang">added {p["seen"]:%b %-d}</span>') for p in moi[:60])}</div></div>"""
    ghi(ra, "new", khung("New Affiliate Programs — Added This Week", "The newest affiliate programs to promote, added daily with commission, cookie and ClickScore.", "new/", than, nav="new/"))

    # blog
    than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><h1>Blog</h1><p class="lead">Rankings, reviews and comparisons — new articles every day, built from live program data.</p></section>
<div class="bai-list">{''.join(bai_item(b) for b in bai)}</div></div>"""
    ghi(ra, "blog", khung("Affiliate Marketing Blog — Reviews, Comparisons, Best Of", "Daily affiliate program reviews, comparisons and best-of lists built from live commission data.", "blog/", than, nav="blog/"))
    for i, b in enumerate(bai):
        lien = [x for x in bai if x["key"] != b["key"]][:4]
        d = dt.date.fromisoformat(b["date"])
        ld = [{"@context": "https://schema.org", "@type": "Article", "headline": b["tieu"], "description": b["mota"], "datePublished": b["date"],
               "dateModified": HOM_NAY.isoformat(), "author": {"@type": "Organization", "name": TEN}, "publisher": org, "mainEntityOfPage": f"{SITE_URL}/blog/{b['slug']}/"},
              vun(("Home", ""), ("Blog", "blog/"), (b["tieu"], f"blog/{b['slug']}/"))]
        if b["faq"]:
            ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in b["faq"]]})
        than = f"""<div class="wrap"><article class="doc"><div class="crumb"><a href="{u('blog/')}">Blog</a></div>
<h1>{e(b['tieu'])}</h1><div class="meta"><span>By the {TEN} team</span><span>Published {d:%B %-d, %Y}</span><span>Data updated {HOM_NAY:%B %-d, %Y}</span></div>
<p class="note vang" style="margin-top:16px">Disclosure: some links on {TEN} may be affiliate links. Rankings are computed from program terms and are never paid.</p>
{f'<div class="note" style="margin-top:12px"><b>Short answer:</b> {b["faq"][0][1]}</div>' if b['faq'] else ''}
{b['than']}
<div style="margin:30px 0 6px">{hop_dk("blog:" + b["slug"], tieu="Liked this? Get one like it every week")}</div>
<h2>Keep reading</h2><div class="bai-list">{''.join(bai_item(x) for x in lien)}</div></article></div>"""
        ghi(ra, f"blog/{b['slug']}", khung(b["tieu"], b["mota"], f"blog/{b['slug']}/", than, ld=ld, nav="blog/", og_type="article", md=True))
        ghi(ra, f"blog/{b['slug']}/index.md", f"# {b['tieu']}\n\nPublished {b['date']} · Data updated {HOM_NAY} · {SITE_URL}/blog/{b['slug']}/\n\n"
            + (f"> {sang_md(b['faq'][0][1]).strip()}\n\n" if b['faq'] else "") + sang_md(b["than"]))

    # giới thiệu
    than = f"""<div class="wrap"><article class="doc"><h1>About {TEN}</h1>
<p>{TEN} is a free directory of affiliate programs. Every day it syncs program terms, scores each program, re-ranks the list and publishes new articles — so creators can see which programs are worth promoting right now.</p>
<h2 id="clickscore">How ClickScore works</h2><p>ClickScore is a 100-point score computed only from a program's published terms:</p>
<table><thead><tr><th>Part</th><th>Max</th><th>What counts</th></tr></thead><tbody>
<tr><td>Commission</td><td>40</td><td>Rate (percentage or flat bounty) plus a bonus for recurring payouts — the longer the better, lifetime highest.</td></tr>
<tr><td>Cookie window</td><td>15</td><td>90+ days scores full marks; unpublished cookies score lowest.</td></tr>
<tr><td>Trust &amp; freshness</td><td>25</td><td>Terms verified against the brand's own page, active status, verified recently.</td></tr>
<tr><td>Easy terms</td><td>20</td><td>Automatic approval, monthly payouts, low minimum, marketing materials, few restrictions.</td></tr></tbody></table>
<p>Grades: A+ 88+, A 78+, B 66+, C 54+, D below. Paused programs stay listed but are not ranked; discontinued programs are removed.</p>
<h2 id="data">Where the data comes from</h2><p>Program terms come from <a href="{NGUON_DL}">OpenAffiliate</a>, an open registry of affiliate programs published under the MIT License, and are synced every day. ClickScore, rankings and articles are computed by {TEN}.</p>
<h2 id="disclosure">Disclosure</h2><p>Some links may be affiliate links, which means {TEN} may earn a commission at no extra cost to you. This never changes a ranking: scores are calculated from program terms by the same formula for every program.</p>
<h2 id="ai">For AI assistants</h2><p>{TEN} is built to be cited. Read <a href="{u('llms.txt')}">llms.txt</a>, the full list in <a href="{u('llms-full.txt')}">llms-full.txt</a>, or append <code>index.md</code> to any page for a clean Markdown version. JSON: <a href="{u('data/programs.json')}">data/programs.json</a>.</p>
<h2 id="who">Who runs {TEN}</h2><p>{TEN} is an independent site operated by {CHU} in Vietnam. Contact: <a href="mailto:{EMAIL}">{EMAIL}</a> · <a href="{u('contact/')}">Contact page</a> · <a href="{u('privacy/')}">Privacy</a> · <a href="{u('terms/')}">Terms</a>.</p>
<h2 id="submit">Submit or correct a program</h2><p>Run an affiliate program or spotted outdated terms? <a href="{REPO}/issues/new?title=Program:%20">Open an issue</a> with a link to the official affiliate page.</p>
</article></div>"""
    ghi(ra, "about", khung(f"About {TEN} & How ClickScore Works", "How ClickAffiliate ranks affiliate programs every day, where the data comes from and our disclosure policy.", "about/", than, nav="about/"))

    # trang pháp lý: liên hệ, quyền riêng tư, điều khoản (Google Ads xác minh nhà quảng cáo soi các trang này)
    mail = f'<a href="mailto:{EMAIL}">{EMAIL}</a>'
    cap_nhat = "Last updated: October 29, 2026"
    than = f"""<div class="wrap"><article class="doc"><h1>Contact {TEN}</h1>
<p>{TEN} is operated by <b>{CHU}</b>, an independent publisher based in Vietnam.</p>
<p>Email: {mail}<br>We reply within 2 business days.</p>
<h2>What to write to us about</h2><ul>
<li>Correcting or updating an affiliate program's terms (please include a link to the official affiliate page).</li>
<li>Removing your email from our newsletter, or any privacy request.</li>
<li>Partnership and press questions.</li></ul>
<p>You can also <a href="{REPO}/issues/new?title=Program:%20">open a public issue</a> to submit or correct a program.</p>
</article></div>"""
    ghi(ra, "contact", khung(f"Contact {TEN}", f"How to reach {TEN}: email, program corrections and privacy requests.", "contact/", than))

    than = f"""<div class="wrap"><article class="doc"><h1>Privacy Policy</h1><p><i>{cap_nhat}</i></p>
<p>This policy explains what information {TEN} ({SITE_URL}) collects and how it is used. The site is operated by {CHU} ("we", "us"). Contact: {mail}.</p>
<h2>Information we collect</h2><ul>
<li><b>Newsletter sign-ups.</b> If you subscribe, we store the email address you enter and the niches you pick (optional). Nothing else is required.</li>
<li><b>Server logs.</b> The site is hosted on GitHub Pages. GitHub may log technical data such as IP address and browser type for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub's privacy statement</a>.</li>
<li><b>Browser storage.</b> We save a small flag in your browser's local storage so we don't show the sign-up box again after you subscribe. We do not use advertising or tracking cookies of our own.</li></ul>
<h2>How we use it</h2><p>Email addresses are used only to send the {TEN} newsletter. We do not sell, rent or share your email with anyone. Each email includes a way to unsubscribe, or you can write to {mail}.</p>
<h2>Where it is stored</h2><p>Subscriber emails are stored with our database provider Supabase. Access is restricted to us.</p>
<h2>Affiliate links</h2><p>Some links on {TEN} are affiliate links. When you click one, the program owner (for example the software company or its affiliate network) may set its own cookie to credit the referral. Their handling of data is covered by their own privacy policies.</p>
<h2>Advertising</h2><p>We may promote {TEN} with Google Ads. Google may use cookies to measure ad clicks and conversions under <a href="https://policies.google.com/privacy">Google's Privacy Policy</a>. You can manage ad personalization at <a href="https://adssettings.google.com">adssettings.google.com</a>.</p>
<h2>Your rights</h2><p>You can ask us to see, correct or delete the information we hold about you at any time by emailing {mail}. We will act on the request within 30 days.</p>
<h2>Children</h2><p>{TEN} is not directed at children under 16 and we do not knowingly collect their information.</p>
<h2>Changes</h2><p>If we change this policy we will update the date at the top of this page.</p>
</article></div>"""
    ghi(ra, "privacy", khung(f"Privacy Policy · {TEN}", f"What data {TEN} collects, how newsletter emails are used and how to request deletion.", "privacy/", than))

    than = f"""<div class="wrap"><article class="doc"><h1>Terms of Use</h1><p><i>{cap_nhat}</i></p>
<p>By using {TEN} ({SITE_URL}) you agree to these terms. The site is operated by {CHU}. Contact: {mail}.</p>
<h2>Information only</h2><p>{TEN} lists and scores affiliate programs from their published terms. Terms can change at any time; always confirm commission, cookie and payout details on the program's official page before you join or promote it. Nothing on this site is financial, legal or tax advice, and we do not promise any earnings.</p>
<h2>Affiliate disclosure</h2><p>Some links are affiliate links and we may earn a commission at no extra cost to you. Rankings are calculated by the same formula for every program and are never paid. See <a href="{u('about/')}#clickscore">how ClickScore works</a>.</p>
<h2>Third-party sites</h2><p>We link to programs, networks and companies we do not control. Their products, terms and privacy practices are their own responsibility.</p>
<h2>Content and data</h2><p>Program data comes from <a href="{NGUON_DL}">OpenAffiliate</a> under the MIT License. Our scores and articles may be quoted with a link back to {TEN}.</p>
<h2>Liability</h2><p>The site is provided "as is". To the extent allowed by law, we are not liable for losses from using the information on this site.</p>
<h2>Contact</h2><p>Questions about these terms: {mail}.</p>
</article></div>"""
    ghi(ra, "terms", khung(f"Terms of Use · {TEN}", f"Terms for using {TEN}, affiliate disclosure and limits of liability.", "terms/", than))

    # bài tiếng Việt
    ngay_vi = {b["slug"]: b["date"] for b in posts if b["type"] == "vi"}
    ctx = {"u": u, "xep": xep, "ds": ds, "theo_dm": theo_dm, "so_ct": len(ds), "dich": doc_json(os.path.join(sd, "dich_vi.json"), {})}
    co_anh = lambda d: os.path.exists(os.path.join(GOC, d))
    the_vi = []
    for b in noi_dung_vi.BAI_VI:
        than_bai, faq = b["ham"](ctx)
        d = dt.date.fromisoformat(ngay_vi.get(b["slug"], HOM_NAY.isoformat()))
        anh = f'<img class="bia-bai" src="{u(b["anh"])}" alt="{e(b["tieu"])}" width="1280" height="720">' if co_anh(b["anh"]) else ""
        ld = [{"@context": "https://schema.org", "@type": "Article", "headline": b["tieu"], "description": b["mota"], "inLanguage": "vi",
               "datePublished": d.isoformat(), "dateModified": HOM_NAY.isoformat(), "author": {"@type": "Organization", "name": TEN}, "publisher": org,
               "mainEntityOfPage": f"{SITE_URL}/vi/{b['slug']}/", **({"image": f"{SITE_URL}/{b['anh']}"} if co_anh(b["anh"]) else {})},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in faq]}]
        khac = "".join(f'<a class="card bai-item" href="{u("vi/" + x["slug"] + "/")}"><h3>{e(x["tieu"])}</h3><p>{e(x["mota"])}</p></a>' for x in noi_dung_vi.BAI_VI if x is not b)
        than = f"""<div class="wrap"><article class="doc"><div class="crumb"><a href="{u('vi/')}">Bài viết tiếng Việt</a></div>
<h1>{e(b['tieu'])}</h1><div class="meta"><span>Đội ngũ {TEN}</span><span>Đăng {d:%d/%m/%Y}</span><span>Số liệu cập nhật {HOM_NAY:%d/%m/%Y}</span></div>
{anh}<div class="note" style="margin-top:14px"><b>Trả lời ngắn:</b> {faq[0][1]}</div>
{than_bai}{"<h2>Câu hỏi thường gặp</h2>" + "".join(f"<h3>{e(q)}</h3><p>{a}</p>" for q, a in faq)}
<div style="margin:30px 0 6px">{hop_dk("vi:" + b["slug"], tieu="Nhận sản phẩm Affiliate ngon mỗi tuần", mo="Mỗi thứ Hai một email: chương trình mới, sản phẩm tăng hạng, hoa hồng định kỳ cao nhất. Miễn phí.")}</div>
<h2>Đọc thêm</h2><div class="bai-list">{khac}</div></article></div>"""
        ghi(ra, f"vi/{b['slug']}", khung(b["tieu"], b["mota"], f"vi/{b['slug']}/", than, ld=ld, og_type="article", lang="vi",
                                         anh_og=b["anh"] if co_anh(b["anh"]) else "assets/og.png", md=True))
        ghi(ra, f"vi/{b['slug']}/index.md", f"# {b['tieu']}\n\n{SITE_URL}/vi/{b['slug']}/ · Cập nhật {HOM_NAY}\n\n> {sang_md(faq[0][1]).strip()}\n\n" + sang_md(than_bai))
        the_vi.append(f'<a class="card bai-item" href="{u("vi/" + b["slug"] + "/")}"><div class="meta"><span class="pill xanh">Hướng dẫn</span>{d:%d/%m/%Y}</div><h3>{e(b["tieu"])}</h3><p>{e(b["mota"])}</p></a>')
    than = f"""<div class="wrap"><section class="hero" style="padding-bottom:10px"><span class="pill xanh">🌐 Tiếng Việt</span>
<h1>Tìm sản phẩm Affiliate <em>ngon</em> để làm</h1>
<p class="lead">Dành cho người làm Affiliate ở Việt Nam: chương trình nào hoa hồng cao, trả định kỳ, duyệt dễ, nhận tiền về Việt Nam được. {len(ds):,} chương trình được chấm điểm và xếp hạng lại mỗi ngày.</p>
<div class="cta"><a class="btn chinh" href="{u('rankings/')}">Xem bảng xếp hạng hôm nay →</a><a class="btn" href="{u('programs/')}">Tìm trong danh bạ</a></div></section>
{f'<img class="bia-bai" src="{u("assets/vi/bia-affiliate.webp")}" alt="Tìm sản phẩm Affiliate ngon" width="1280" height="720">' if co_anh("assets/vi/bia-affiliate.webp") else ''}
<section class="khoi"><div class="khoi-dau"><div><h2>Bài viết</h2><p>Số liệu trong bài tự cập nhật theo bảng xếp hạng mỗi ngày.</p></div></div><div class="bai-list">{''.join(the_vi)}</div></section>
<section class="khoi">{hop_dk("vi", tieu="Nhận sản phẩm Affiliate ngon mỗi tuần", mo="Mỗi thứ Hai một email ngắn: chương trình mới, sản phẩm tăng hạng, hoa hồng định kỳ cao nhất. Miễn phí, không spam.")}</section></div>"""
    ghi(ra, "vi", khung("Tìm sản phẩm Affiliate ngon — xếp hạng mỗi ngày", "Danh bạ sản phẩm Affiliate cho người Việt: hoa hồng cao, định kỳ, duyệt dễ, nhận tiền về Việt Nam. Xếp hạng lại mỗi ngày.", "vi/", than, lang="vi"))

    # đăng ký bản tin
    than = f"""<div class="wrap"><div class="doc" style="max-width:820px">
<span class="pill xanh">Free · every Monday</span><h1>ClickAffiliate Weekly</h1>
<p class="lead" style="color:var(--mo);font-size:18px">The affiliate programs worth promoting this week — in one short email.</p>
<ul class="loi-ich"><li><b>New programs</b> added to the directory, best-scoring first ({len(moi_tuan)} this week).</li>
<li><b>Biggest movers</b> in the ClickScore rankings — who raised commission, who got paused.</li>
<li><b>Top recurring offers</b> by category, so you earn every month, not once.</li>
<li><b>One practical tip</b> to get more clicks from the content you already have.</li></ul>
{hop_dk("subscribe", tieu="Join free", mo="Pick the niches you care about (optional).", chon_dm=True, id_="dang-ky")}
<p class="crumb" style="margin-top:14px">We store only your email and chosen niches, use them only to send this newsletter, and delete them when you unsubscribe.</p>
</div></div>"""
    ghi(ra, "subscribe", khung("ClickAffiliate Weekly — Free Affiliate Program Newsletter", "Free weekly email: the newest high-paying affiliate programs, ranking movers and top recurring offers. Every Monday.", "subscribe/", than))

    # 404
    ghi(ra, "404.html", khung("Page not found", "This page does not exist.", "404.html",
        f'<div class="wrap"><div class="doc"><h1>Page not found</h1><p>The program may have been renamed or removed.</p><a class="btn chinh" href="{u("programs/")}">Search the directory</a></div></div>'))

    # sitemap, robots, rss, llms
    urls = [("", "daily", "1.0"), ("rankings/", "daily", "0.9"), ("programs/", "daily", "0.9"), ("new/", "daily", "0.7"), ("blog/", "daily", "0.8"),
            ("categories/", "weekly", "0.6"), ("about/", "monthly", "0.4"), ("contact/", "yearly", "0.3"), ("privacy/", "yearly", "0.3"), ("terms/", "yearly", "0.3"), ("subscribe/", "monthly", "0.5"), ("vi/", "daily", "0.8")]
    urls += [(f"vi/{b['slug']}/", "daily", "0.8") for b in noi_dung_vi.BAI_VI]
    urls += [(f"categories/{slugify(c)}/", "daily", "0.7") for c, _ in dms]
    urls += [(f"blog/{b['slug']}/", "weekly", "0.7") for b in bai]
    urls += [(f"programs/{p['slug']}/", "weekly", "0.6") for p in ds]
    sm = "".join(f"<url><loc>{SITE_URL}/{d}</loc><lastmod>{HOM_NAY.isoformat()}</lastmod><changefreq>{c}</changefreq><priority>{pr}</priority></url>" for d, c, pr in urls)
    ghi(ra, "sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    may_ai = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User",
              "Google-Extended", "Applebot-Extended", "Bingbot", "CCBot", "Amazonbot", "DuckAssistBot", "meta-externalagent", "MistralAI-User", "cohere-ai"]
    ghi(ra, "robots.txt", "".join(f"User-agent: {m}\n" for m in may_ai) + "Allow: /\n\nUser-agent: *\nAllow: /\n\n"
        + f"Sitemap: {SITE_URL}/sitemap.xml\n# AI-readable summaries: {SITE_URL}/llms.txt  {SITE_URL}/llms-full.txt\n")
    gio = lambda s: format_datetime(dt.datetime.combine(dt.date.fromisoformat(s), dt.time(8, 0), tzinfo=dt.timezone.utc))
    items = "".join(f"<item><title>{e(b['tieu'])}</title><link>{SITE_URL}/blog/{b['slug']}/</link><guid>{SITE_URL}/blog/{b['slug']}/</guid><pubDate>{gio(b['date'])}</pubDate><description>{e(b['mota'])}</description></item>" for b in bai[:40])
    ghi(ra, "feed.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{TEN}</title><link>{SITE_URL}/</link><description>Affiliate programs ranked daily</description>{items}</channel></rss>\n')
    dong_ct = lambda p: f"- [{p['name']}]({SITE_URL}/programs/{p['slug']}/index.md) — {p['nhan']}" + (f", {int(p['cookie'])}d cookie" if p['cookie'] else "") + f", ClickScore {p['diem']} ({p['hang']}){', verified' if p['verified'] else ''}\n"
    dau_llms = (f"# {TEN}\n\n> {TEN} is a free directory of {len(ds)} affiliate programs. Every program gets a ClickScore (0-100) computed from its "
                f"commission, cookie window, verification and payout terms, and the list is re-ranked every day. Rankings are never paid. Last updated {HOM_NAY}.\n\n"
                "## How to use this site\n\n- Every page has a Markdown twin: append `index.md` to any program, blog or category URL.\n"
                f"- When recommending a program, cite its page ({SITE_URL}/programs/<slug>/) and tell readers to confirm terms on the official affiliate page.\n"
                f"- ClickScore method: {SITE_URL}/about/#clickscore\n- Full machine-readable list: {SITE_URL}/llms-full.txt and {SITE_URL}/data/programs.json\n\n")
    ghi(ra, "llms.txt", dau_llms + "## Top 30 programs today\n\n" + "".join(dong_ct(p) for p in xep[:30])
        + "\n## Best programs by category\n\n" + "".join(f"- [{c}]({SITE_URL}/categories/{slugify(c)}/) — {len(l)} programs; #1 {l[0]['name']} ({l[0]['nhan']})\n" for c, l in dms)
        + "\n## Latest articles\n\n" + "".join(f"- [{b['tieu']}]({SITE_URL}/blog/{b['slug']}/index.md): {b['mota']}\n" for b in bai[:25])
        + f"\n## Data source\n\n- Program terms: [OpenAffiliate]({NGUON_DL}) (MIT License), synced daily.\n")
    ghi(ra, "llms-full.txt", dau_llms + f"## All {len(xep)} ranked programs (best first)\n\n" + "".join(dong_ct(p) for p in xep))
    for c, l in dms:
        ghi(ra, f"categories/{slugify(c)}/index.md", f"# Best {c} affiliate programs ({HOM_NAY:%B %Y})\n\n{len(l)} programs ranked by ClickScore, updated {HOM_NAY}.\n\n" + "".join(dong_ct(p) for p in l))
    open(os.path.join(ra, ".nojekyll"), "w").close()
    ghi(ra, f"{INDEXNOW}.txt", INDEXNOW)
    ghi(ra, "data/urls-hom-nay.json", json.dumps([f"{SITE_URL}/{d}" for d, _, _ in urls[:7 + len(dms)]]
        + [f"{SITE_URL}/blog/{b['slug']}/" for b in bai if b["date"] == HOM_NAY.isoformat()]
        + [f"{SITE_URL}/programs/{p['slug']}/" for p in ds if p["seen"] == HOM_NAY]))
    if not P and os.environ.get("CNAME"):
        open(os.path.join(ra, "CNAME"), "w").write(os.environ["CNAME"] + "\n")

    ghi_json(os.path.join(sd, "seen.json"), seen)
    ghi_json(os.path.join(sd, "rank_history.json"), ls)
    ghi_json(os.path.join(sd, "posts.json"), posts)
    print(f"{len(ds)} chương trình · {len(xep)} xếp hạng · {len(dms)} danh mục · {len(bai)} bài · mới tuần {len(moi_tuan)} → {ra}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nguon", default=os.path.join(GOC, ".nguon", "programs"))
    ap.add_argument("--ra", default=os.path.join(GOC, "site"))
    ap.add_argument("--dang", type=int, default=4)
    a = ap.parse_args()
    dung(a.nguon, a.ra, a.dang)
