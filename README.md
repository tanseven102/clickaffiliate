# ClickAffiliate

Trang: https://clickaffiliate.net — Danh bạ chương trình affiliate kiểu openaffiliate.dev — tự xếp hạng và tự viết bài SEO mỗi ngày.

- **Mỗi ngày 08:00 (giờ VN)** GitHub Actions (`.github/workflows/hang-ngay.yml`) tự chạy:
  kéo dữ liệu mới từ OpenAffiliate (MIT) → chấm ClickScore → xếp hạng lại (có mũi tên lên/xuống so hôm qua)
  → đăng thêm 4 bài (Best of theo danh mục · Review · So sánh A vs B · Tổng hợp chương trình mới mỗi tuần)
  → đưa lên GitHub Pages.
- Sổ trạng thái nằm ở `state/` (ngày thấy lần đầu, lịch sử hạng 30 ngày, danh sách bài đã đăng) — máy tự commit.
- Dựng thử ở máy: `python3 build.py --dang 0` (ra thư mục `site/`). Logo: `assets/logo.svg`, PNG vẽ bằng `tools/ve_logo.py`.

## Gắn tên miền riêng
1. Mua tên miền (vd `clickaffiliate.net`) ở Cloudflare Registrar.
2. Cloudflare DNS: thêm 4 bản ghi A `@` → 185.199.108.153 / .109.153 / .110.153 / .111.153 (DNS only), và CNAME `www` → `tanseven102.github.io`.
3. Repo → Settings → Secrets and variables → Actions → Variables: `SITE_URL=https://clickaffiliate.net`, `CNAME=clickaffiliate.net`.
4. Settings → Pages → Custom domain: `clickaffiliate.net`, bật Enforce HTTPS. Chạy lại workflow.
5. Google Search Console: thêm tên miền, nộp `https://clickaffiliate.net/sitemap.xml`.
