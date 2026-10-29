#!/usr/bin/env python3
"""Xem lượt vào ClickAffiliate (đọc bằng quyền chủ qua Supabase CLI bên Windows, như xem_email.py).
   python3 tools/xem_luot.py [số ngày, mặc định 7]
"""
import json, os, subprocess, sys

NGAY = int(sys.argv[1]) if len(sys.argv) > 1 else 7
TMP = "/mnt/c/Users/tan/AppData/Local/Temp/ca"
os.makedirs(TMP, exist_ok=True)
T = f"from public.clickaffiliate_views where created_at > now() - interval '{NGAY} days'"
CAU = {
    "ngay": f"select to_char(created_at at time zone 'Asia/Ho_Chi_Minh','MM-DD') as n, count(*) filter (where loai='xem') as luot, "
            f"count(distinct khach) as nguoi, count(*) filter (where loai='go') as click {T} group by 1 order by 1",
    "trang": f"select path, count(*) as luot {T} and loai='xem' group by 1 order by 2 desc limit 10",
    "nguon": f"select coalesce(ref,'(gõ thẳng / không rõ)') as ref, count(*) as luot {T} group by 1 order by 2 desc limit 10",
    "click": f"select path, coalesce(k,'(web)') as kenh, count(*) as click {T} and loai='go' group by 1,2 order by 3 desc limit 20",
}

def hoi(sql):
    open(f"{TMP}/luot.sql", "w").write(sql + ";")
    lenh = ("cd C:\\Users\\tan\\tanseven-voice-web; npx.cmd -y supabase@latest db query --linked "
            "--project-ref idnfafxgrbabypfokgve -o json -f C:\\Users\\tan\\AppData\\Local\\Temp\\ca\\luot.sql")
    ra = subprocess.run(["powershell.exe", "-NoProfile", "-Command", lenh], capture_output=True, text=True).stdout
    return json.loads(ra[ra.find("["):ra.rfind("]") + 1] or "[]")

print(f"== {NGAY} ngày qua ==\nNgày   Lượt xem  Người  Click aff")
for d in hoi(CAU["ngay"]):
    print(f"{d['n']}  {d['luot']:>8}  {d['nguoi']:>5}  {d['click']:>9}")
for ten, cot in (("trang", "path"), ("nguon", "ref")):
    print(f"\n-- {'Trang xem nhiều' if ten == 'trang' else 'Khách tới từ'} --")
    for d in hoi(CAU[ten]):
        print(f"{d['luot']:>6}  {d[cot]}")
print("\n-- Click link affiliate (theo kênh ?k=) --")
for d in hoi(CAU["click"]):
    print(f"{d['click']:>6}  {d['path']:<28} {d['kenh']}")
