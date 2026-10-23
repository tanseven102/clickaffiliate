#!/usr/bin/env python3
"""Xem / xuất danh sách email đăng ký ClickAffiliate (đọc bằng quyền chủ qua Supabase CLI bên Windows).
   python3 tools/xem_email.py          → in bảng
   python3 tools/xem_email.py --csv    → ghi Desktop\\ClickAffiliate-email.csv
"""
import csv, json, os, subprocess, sys

TMP = "/mnt/c/Users/tan/AppData/Local/Temp/ca"
os.makedirs(TMP, exist_ok=True)
open(f"{TMP}/xem.sql", "w").write(
    "select email, source, interests, to_char(created_at at time zone 'Asia/Ho_Chi_Minh','YYYY-MM-DD HH24:MI') as luc "
    "from public.clickaffiliate_subscribers where email not like '%@clickaffiliate.test' order by created_at desc;")
lenh = ("cd C:\\Users\\tan\\tanseven-voice-web; npx.cmd -y supabase@latest db query --linked "
        "--project-ref idnfafxgrbabypfokgve -o json -f C:\\Users\\tan\\AppData\\Local\\Temp\\ca\\xem.sql")
ra = subprocess.run(["powershell.exe", "-NoProfile", "-Command", lenh], capture_output=True, text=True).stdout
dong = json.loads(ra[ra.find("["):ra.rfind("]") + 1] or "[]")
if "--csv" in sys.argv:
    f = "/mnt/c/Users/tan/Desktop/ClickAffiliate-email.csv"
    with open(f, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["email", "source", "interests", "luc"]); w.writeheader(); w.writerows(dong)
    print(f"Đã ghi {len(dong)} email → Desktop\\ClickAffiliate-email.csv")
else:
    print(f"{len(dong)} email")
    for d in dong:
        print(f"{d['luc']}  {d['email']:<40} {d.get('interests') or ''}  ({d['source']})")
