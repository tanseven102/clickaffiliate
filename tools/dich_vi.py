#!/usr/bin/env python3
"""Dịch mô tả ngắn + luật cấm của các chương trình điểm cao sang tiếng Việt (cho mục /vi/).

Chạy ở máy chính (có khoá OpenAI của FUNNY), lưu vào state/dich_vi.json rồi commit — máy dựng trên GitHub
chỉ đọc file đó, không gọi OpenAI. Câu nào đã dịch (cùng nội dung gốc) thì không dịch lại.
   python3 tools/dich_vi.py [--so 300]
Trần chi: state/openai_chi.json đếm token theo ngày; vượt TRAN_TOKEN_NGAY thì dừng.
"""
import argparse, datetime as dt, hashlib, json, os, re, sys, urllib.request

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
import build  # noqa: E402

MODEL = "gpt-5.4-mini"
TRAN_TOKEN_NGAY = 400_000          # ~ vài nghìn đồng/ngày với model mini — trần cứng
F_DICH = os.path.join(GOC, "state", "dich_vi.json")
F_CHI = os.path.join(GOC, "state", "openai_chi.json")


def khoa():
    s = open("/mnt/c/Users/tan/tan-seven-vui/api_key.txt", encoding="utf-8", errors="ignore").read()
    m = re.search(r"sk-[A-Za-z0-9_-]+", s)
    if not m:
        sys.exit("Không thấy khoá OpenAI trong api_key.txt của FUNNY")
    return m.group(0)


def bam(s):
    return hashlib.md5(s.encode()).hexdigest()[:10]


def goi(cau, k):
    """Gửi một lô câu, nhận lại danh sách bản dịch cùng thứ tự."""
    chi = build.doc_json(F_CHI, {})
    hom = dt.date.today().isoformat()
    if chi.get(hom, 0) > TRAN_TOKEN_NGAY:
        sys.exit(f"Đã chạm trần {TRAN_TOKEN_NGAY:,} token hôm nay — dừng")
    than = {"model": MODEL, "response_format": {"type": "json_object"}, "messages": [
        {"role": "system", "content": "Bạn dịch mô tả sản phẩm phần mềm và luật chương trình affiliate từ tiếng Anh sang tiếng Việt tự nhiên, "
         "ngắn gọn, giữ nguyên tên thương hiệu, con số, đơn vị tiền. Không thêm ý. Trả JSON {\"dich\": [...]} đúng số phần tử, đúng thứ tự."},
        {"role": "user", "content": json.dumps({"cau": cau}, ensure_ascii=False)}]}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", json.dumps(than).encode(),
                                 {"Authorization": "Bearer " + k, "Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    chi[hom] = chi.get(hom, 0) + r["usage"]["total_tokens"]
    build.ghi_json(F_CHI, chi)
    ra = json.loads(r["choices"][0]["message"]["content"])["dich"]
    if len(ra) != len(cau):
        raise ValueError(f"lô trả {len(ra)} câu, cần {len(cau)}")
    return ra, r["usage"]["total_tokens"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--so", type=int, default=300)
    a = ap.parse_args()
    ds = build.doc_chuong_trinh(os.path.join(GOC, ".nguon", "programs"))
    for p in ds:
        build.cham_diem(p)
    ds.sort(key=lambda p: -p["diem"])
    dich = build.doc_json(F_DICH, {})
    can = []  # (khoá lưu, câu gốc)
    for p in ds[:a.so]:
        for loai, goc in [("ngan", p["ngan"])] + [(f"luat{i}", x) for i, x in enumerate(p["restrictions"][:3])]:
            k = f"{p['slug']}|{loai}"
            if goc and dich.get(k, {}).get("h") != bam(goc):
                can.append((k, goc))
    print(f"Cần dịch {len(can)} câu")
    kk, tong = khoa(), 0
    for i in range(0, len(can), 40):
        lo = can[i:i + 40]
        try:
            ra, tk = goi([c for _, c in lo], kk)
            ket = [(lo, ra)]
        except ValueError:          # thiếu/thừa câu → chia lô nhỏ 8 câu dịch lại
            ket, tk = [], 0
            for j in range(0, len(lo), 8):
                nho = lo[j:j + 8]
                try:
                    r2, t2 = goi([c for _, c in nho], kk)
                    ket.append((nho, r2)); tk += t2
                except ValueError as loi:
                    print("  bỏ lô nhỏ:", loi)
        tong += tk
        for nho, ra in ket:
            for (k, goc), vi in zip(nho, ra):
                dich[k] = {"h": bam(goc), "vi": str(vi).strip()}
        build.ghi_json(F_DICH, dich)
        print(f"  lô {i // 40 + 1}: {len(lo)} câu, {tk:,} token")
    print(f"Xong. {tong:,} token lần này.")


if __name__ == "__main__":
    main()
