"""Bài viết tiếng Việt cho người làm Affiliate đang tìm sản phẩm ngon (anh Tân 23/10/2026).

Mỗi bài là một hàm nhận bộ dữ liệu hôm nay (ctx) và trả HTML — bảng, con số, tên sản phẩm luôn lấy từ
bảng xếp hạng hiện tại, nên bài tự mới mỗi ngày dù lời văn giữ nguyên.
"""
import collections
import re
import html

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def _tl(ctx, p, loai, goc):
    """Bản dịch tiếng Việt (state/dich_vi.json) nếu có, không thì giữ câu gốc."""
    return ctx["dich"].get(f"{p['slug']}|{loai}", {}).get("vi") or goc


def _vi_hh(p):
    """Nhãn hoa hồng tiếng Việt."""
    c = p["c"]
    rate = re.sub(r"(?i)^up to\s+", "tới ", c["rate"] or "Tuỳ gói")
    rate = re.sub(r"(\d%?)\s+to\s+(\$?\d)", r"\1–\2", rate).replace(" per ", "/")
    if c["type"] == "recurring":
        d = str(c["duration"] or "").lower()
        if "lifetime" in d:
            return f"{rate} định kỳ, trọn đời"
        if d:
            return f"{rate} định kỳ, {d.replace('months', 'tháng').replace('month', 'tháng').replace('years', 'năm').replace('year', 'năm')}"
        return f"{rate} định kỳ"
    if c["type"] == "one-time":
        return f"{rate} một lần"
    return f"{rate} ({'nhiều bậc' if c['type'] == 'tiered' else 'kết hợp'})"


def _cookie(p):
    return f"{int(p['cookie'])} ngày" if p["cookie"] else "không công bố"


def _duyet(p):
    return {"auto": "tự động", "automatic": "tự động", "manual": "xét tay", "invite-only": "chỉ mời"}.get(p["approval"], "không công bố")


def _bang(ctx, ds):
    u = ctx["u"]
    hang = "".join(
        f"<tr><td>{i}</td><td><a href=\"{u('programs/' + p['slug'] + '/')}\">{e(p['name'])}</a></td><td>{e(_vi_hh(p))}</td>"
        f"<td>{_cookie(p)}</td><td>{_duyet(p)}</td><td><b>{p['diem']}</b> ({e(p['hang'])})</td></tr>" for i, p in enumerate(ds, 1))
    return ("<table><thead><tr><th>#</th><th>Sản phẩm</th><th>Hoa hồng</th><th>Cookie</th><th>Duyệt</th><th>ClickScore</th></tr></thead>"
            f"<tbody>{hang}</tbody></table>")


def _the(ctx, p, so):
    u = ctx["u"]
    tan = p["payout"]
    tra = (tan.get("frequency") or "").replace("monthly", "hằng tháng").replace("net-30", "sau 30 ngày").replace("net-60", "sau 60 ngày")
    ten_pp = {"paypal": "PayPal", "bank": "chuyển khoản", "stripe": "Stripe", "wise": "Wise", "payoneer": "Payoneer", "crypto": "tiền mã hoá", "check": "séc"}
    pp = ", ".join(ten_pp.get(m, m) for m in (tan.get("methods") or []))
    luat = f" Lưu ý luật: <i>{e(_tl(ctx, p, 'luat0', p['restrictions'][0]))}</i>" if p["restrictions"] else ""
    luat = luat + ("" if not luat or luat.endswith((".", "!")) else ".")
    return (f"<h3>{so}. <a href=\"{u('programs/' + p['slug'] + '/')}\">{e(p['name'])}</a> — {e(_vi_hh(p))}</h3>"
            f"<p><b>Là gì:</b> {e(_tl(ctx, p, 'ngan', p['ngan']))}</p>"
            f"<p><b>Điều khoản:</b> hoa hồng {e(_vi_hh(p))}, cookie {_cookie(p)}, duyệt {_duyet(p)}"
            + (f", trả tiền {e(tra)}" if tra else "") + (f" qua {e(pp)}" if pp else "") + f". ClickScore <b>{p['diem']}/100</b>.{luat}</p>")


# ───────────────────────── 1. Top định kỳ trọn đời ─────────────────────────

def bai_tron_doi(ctx):
    ds = [p for p in ctx["xep"] if p["c"]["type"] == "recurring" and "lifetime" in str(p["c"]["duration"] or "").lower()][:10]
    tong = sum(1 for p in ctx["xep"] if p["c"]["type"] == "recurring" and "lifetime" in str(p["c"]["duration"] or "").lower())
    vi_du = ds[0] if ds else None
    than = f"""<p>Nếu bạn làm Affiliate được một thời gian, bạn sẽ thấy một sự thật: <b>hoa hồng một lần</b> giống như làm công nhật — giới thiệu xong, nhận tiền, hết. Còn <b>hoa hồng định kỳ trọn đời</b> thì giống trồng cây: khách bạn giới thiệu còn trả tiền phần mềm tháng nào, bạn còn nhận tiền tháng đó, có khi kéo dài nhiều năm.</p>
<p>Trong {ctx['so_ct']:,} chương trình ClickAffiliate đang theo dõi, chỉ có <b>{tong}</b> chương trình trả định kỳ trọn đời. Dưới đây là 10 chương trình có điểm ClickScore cao nhất hôm nay — điểm chấm từ hoa hồng, thời gian cookie, độ tin cậy của điều khoản và độ dễ khi nhận tiền.</p>
<div class="note"><b>Tóm tắt nhanh:</b> {('đứng đầu hôm nay là <b>' + e(vi_du['name']) + '</b> (' + e(_vi_hh(vi_du)) + ', cookie ' + _cookie(vi_du) + ').') if vi_du else ''} Bảng tự cập nhật mỗi ngày theo bảng xếp hạng.</div>
<h2>Bảng xếp hạng hôm nay</h2>{_bang(ctx, ds)}
<h2>Vì sao "trọn đời" đáng giá hơn bạn nghĩ</h2>
<p>Ví dụ dễ hiểu: một phần mềm giá <b>$30/tháng</b>, chương trình trả <b>30% trọn đời</b>. Mỗi khách bạn giới thiệu mang về $9/tháng. Nếu trung bình khách dùng 2 năm, một khách = <b>$216</b>. Có 50 khách đang dùng cùng lúc là khoảng <b>$450 mỗi tháng</b> đều đặn — trong khi bạn không phải làm thêm gì cho những khách cũ đó.</p>
<p>So với hoa hồng một lần $50/khách, bạn phải liên tục tìm khách mới mới giữ được thu nhập.</p>
<h2>Chi tiết từng chương trình</h2>{''.join(_the(ctx, p, i) for i, p in enumerate(ds, 1))}
<h2>3 lưu ý trước khi đăng ký</h2>
<ul><li><b>"Trọn đời" thường có điều kiện</b> — đọc kỹ dòng chữ nhỏ: có nơi giới hạn mức trần mỗi khách, có nơi ngừng trả nếu tài khoản affiliate không hoạt động vài tháng.</li>
<li><b>Ưu tiên chương trình đã xác minh</b> (có dấu ✓ verified trên ClickAffiliate): điều khoản đã được đối chiếu với trang gốc của hãng.</li>
<li><b>Chọn sản phẩm bạn hiểu</b>: khán giả của bạn đang cần gì thì làm sản phẩm đó, đừng chọn chỉ vì phần trăm cao.</li></ul>
<p>Xem toàn bộ bảng xếp hạng ở <a href="{ctx['u']('rankings/')}">Top 100 chương trình Affiliate</a>, hoặc lọc theo "Recurring" trong <a href="{ctx['u']('programs/')}">danh bạ</a>.</p>"""
    faq = [("Hoa hồng định kỳ trọn đời là gì?", "Là kiểu hoa hồng mà bạn nhận tiền mỗi kỳ khách thanh toán (thường hằng tháng) trong suốt thời gian khách còn dùng sản phẩm, không giới hạn số tháng."),
           ("Chương trình trọn đời nào tốt nhất hiện nay?", f"Theo ClickScore hôm nay là {e(vi_du['name'])} ({e(_vi_hh(vi_du))})." if vi_du else "Xem bảng xếp hạng phía trên."),
           ("Người Việt có tham gia được không?", "Đa số chương trình nhận đối tác toàn cầu và trả qua PayPal, Stripe hoặc chuyển khoản quốc tế. Hãy kiểm tra mục phương thức thanh toán của từng chương trình.")]
    return than, faq


# ───────────────────────── 2. Cách chọn sản phẩm ngon ─────────────────────────

def bai_chon_san_pham(ctx):
    vd = ctx["xep"][0]
    than = f"""<p>Câu hỏi người mới làm Affiliate hỏi nhiều nhất: <b>"Làm sản phẩm nào cho ra tiền?"</b>. Câu trả lời ngắn: sản phẩm ngon không phải sản phẩm có phần trăm cao nhất, mà là sản phẩm <b>khán giả của bạn cần</b> và có <b>điều khoản tốt</b>. Bài này chỉ bạn 6 tiêu chí để soi một chương trình trong 5 phút.</p>
<h2>1. Hoa hồng: nhìn cả phần trăm lẫn "định kỳ hay một lần"</h2>
<p>30% của gói $10 khác hoàn toàn 30% của gói $300. Và 20% định kỳ 12 tháng thường lời hơn 40% một lần. Luôn tính ra <b>số tiền trên mỗi khách</b>, không nhìn phần trăm suông.</p>
<h2>2. Cookie: càng dài càng dễ ăn tiền</h2>
<p>Cookie là khoảng thời gian sau khi người xem bấm link mà nếu họ mua, bạn vẫn được tính. Phần mềm thường được cân nhắc vài tuần mới mua, nên <b>cookie 60–90 ngày trở lên</b> là đẹp; dưới 30 ngày thì thiệt.</p>
<h2>3. Điều khoản đã được xác minh chưa</h2>
<p>Rất nhiều danh sách trên mạng chép số liệu cũ. Trên ClickAffiliate, chương trình có dấu <b>✓ verified</b> nghĩa là điều khoản đã được đối chiếu với trang affiliate chính thức của hãng, kèm ngày kiểm tra.</p>
<h2>4. Duyệt tự động hay xét tay</h2>
<p>Duyệt tự động thì đăng ký xong làm được ngay. Xét tay thường mất 1–5 ngày và có thể bị từ chối nếu bạn chưa có kênh, website. Người mới nên bắt đầu từ chương trình duyệt tự động.</p>
<h2>5. Nhận tiền có dễ không</h2>
<p>Xem 3 thứ: <b>trả bao lâu một lần</b> (hằng tháng là tốt), <b>mức tối thiểu để rút</b> (càng thấp càng tốt, $50 trở xuống là ổn) và <b>phương thức</b> (PayPal, Stripe, chuyển khoản) có dùng được ở Việt Nam không.</p>
<h2>6. Luật cấm — đọc trước khi làm</h2>
<p>Lỗi hay gặp nhất khiến bị khoá tài khoản và mất hoa hồng: chạy quảng cáo Google bằng tên thương hiệu, tự mua qua link của mình, đăng mã giảm giá lên trang coupon. Mỗi trang chương trình trên ClickAffiliate đều có mục <b>Restrictions</b> liệt kê các luật này.</p>
<h2>Ví dụ: soi nhanh chương trình đang đứng #1</h2>
<p><b>{e(vd['name'])}</b>: hoa hồng {e(_vi_hh(vd))}, cookie {_cookie(vd)}, duyệt {_duyet(vd)}. ClickScore <b>{vd['diem']}/100</b> — điểm từng phần:</p>
<table><thead><tr><th>Phần</th><th>Điểm</th></tr></thead><tbody>{''.join(f"<tr><td>{dict(Commission='Hoa hồng', **{'Cookie window': 'Cookie', 'Trust & freshness': 'Độ tin cậy', 'Easy terms': 'Điều khoản dễ'}).get(k, k)}</td><td>{v}/{m}</td></tr>" for k, v, m in vd['chia'])}</tbody></table>
<h2>Làm nhanh hơn với ClickAffiliate</h2>
<p>Bạn không cần tự soi tay hàng nghìn chương trình: <a href="{ctx['u']('rankings/')}">bảng xếp hạng</a> đã chấm điểm sẵn theo đúng 6 tiêu chí trên và cập nhật mỗi ngày. Lọc theo ngách trong <a href="{ctx['u']('categories/')}">danh mục</a> để tìm sản phẩm hợp với khán giả của bạn.</p>"""
    faq = [("Sản phẩm Affiliate nào dễ ra đơn nhất cho người mới?", "Sản phẩm giải quyết đúng vấn đề khán giả của bạn đang gặp, có duyệt tự động, cookie dài và hoa hồng định kỳ."),
           ("Có nên chọn chương trình hoa hồng cao nhất?", "Không nên chỉ nhìn phần trăm. Hãy tính số tiền trên mỗi khách và xem cookie, điều khoản nhận tiền, luật cấm.")]
    return than, faq


# ───────────────────────── 3. Làm Affiliate quốc tế từ Việt Nam ─────────────────────────

def bai_tu_viet_nam(ctx):
    ds = ctx["ds"]
    dem = collections.Counter(m for p in ds for m in (p["payout"].get("methods") or []))
    co_pp = sum(1 for p in ds if p["payout"].get("methods"))
    ty = lambda k: round(100 * dem.get(k, 0) / co_pp) if co_pp else 0
    de = [p for p in ctx["xep"] if p["approval"] in ("auto", "automatic") and "paypal" in (p["payout"].get("methods") or [])][:8]
    than = f"""<p>Thị trường Affiliate quốc tế trả bằng đô la, hoa hồng phần mềm thường 20–50%, và phần lớn chương trình <b>nhận đối tác ở mọi quốc gia</b> — kể cả Việt Nam. Bài này tổng hợp những gì bạn cần biết để bắt đầu: chọn sản phẩm, nhận tiền về Việt Nam và tránh bị khoá tài khoản.</p>
<h2>Các chương trình trả tiền bằng cách nào?</h2>
<p>Trong {co_pp:,} chương trình có công bố phương thức thanh toán mà ClickAffiliate theo dõi:</p>
<table><thead><tr><th>Phương thức</th><th>Tỉ lệ chương trình hỗ trợ</th></tr></thead><tbody>
<tr><td>PayPal</td><td>{ty('paypal')}%</td></tr><tr><td>Chuyển khoản ngân hàng</td><td>{ty('bank')}%</td></tr><tr><td>Stripe</td><td>{ty('stripe')}%</td></tr><tr><td>Wise</td><td>{ty('wise')}%</td></tr></tbody></table>
<p>Với người ở Việt Nam, <b>PayPal</b> là cách phổ biến nhất (rút về ngân hàng Việt Nam được). Chuyển khoản quốc tế (SWIFT) cũng nhận được nhưng phí mỗi lần thường cao hơn, nên phù hợp khi số tiền lớn.</p>
<h2>Chương trình duyệt tự động, trả qua PayPal — hợp người mới</h2>{_bang(ctx, de)}
<h2>5 lỗi khiến người Việt hay bị khoá tài khoản</h2>
<ol><li><b>Tự mua qua link của mình</b> hoặc nhờ người nhà mua — gần như mọi chương trình đều cấm.</li>
<li><b>Chạy quảng cáo bằng tên thương hiệu</b> (vd quảng cáo Google từ khoá "Tên hãng") khi chương trình không cho phép.</li>
<li><b>Khai thông tin sai</b> khi đăng ký (tên, quốc gia, website) — đến lúc rút tiền bị đối chiếu và giữ lại.</li>
<li><b>Spam link</b> vào nhóm, bình luận hàng loạt — hãng nhận được báo cáo là khoá ngay.</li>
<li><b>Không ghi chú link affiliate</b> cho người xem — nhiều chương trình bắt buộc phải công khai.</li></ol>
<h2>Bắt đầu thế nào trong 1 tuần</h2>
<ul><li><b>Ngày 1–2:</b> chọn 1 ngách bạn hiểu (AI, thiết kế, marketing…) trong <a href="{ctx['u']('categories/')}">danh mục</a>.</li>
<li><b>Ngày 3:</b> chọn 3 chương trình điểm cao, duyệt tự động, trả qua PayPal.</li>
<li><b>Ngày 4–7:</b> làm 3 nội dung: một bài/video review, một bài so sánh "A vs B", một bài hướng dẫn dùng. Đây là 3 dạng ra đơn tốt nhất vì người xem đang có ý định mua.</li></ul>"""
    faq = [("Người Việt Nam có làm Affiliate quốc tế được không?", "Được. Đa số chương trình phần mềm nhận đối tác toàn cầu; bạn chỉ cần khai đúng thông tin và có phương thức nhận tiền như PayPal."),
           ("Nhận tiền Affiliate về Việt Nam bằng cách nào?", f"Phổ biến nhất là PayPal ({ty('paypal')}% chương trình hỗ trợ), sau đó rút về tài khoản ngân hàng Việt Nam. Chuyển khoản quốc tế cũng được nhưng phí cao hơn.")]
    return than, faq


# ───────────────────────── 4. Sản phẩm AI cho người mới ─────────────────────────

def bai_ai_nguoi_moi(ctx):
    ai = ctx["theo_dm"].get("AI", [])
    ds = sorted([p for p in ai if p["approval"] in ("auto", "automatic")], key=lambda p: -p["diem"])[:4]
    ds += [p for p in ai if p not in ds][: 7 - len(ds)]
    than = f"""<p>AI là ngách Affiliate nóng nhất hiện nay: người dùng tìm kiếm công cụ AI mỗi ngày, phần mềm thu phí theo tháng nên hoa hồng thường là <b>định kỳ</b>. ClickAffiliate đang theo dõi <b>{len(ai)}</b> chương trình AI. Đây là 7 chương trình hợp với người mới nhất hôm nay — ưu tiên duyệt tự động và điểm cao.</p>
<h2>Bảng so sánh</h2>{_bang(ctx, ds)}
<h2>Từng sản phẩm</h2>{''.join(_the(ctx, p, i) for i, p in enumerate(ds, 1))}
<h2>Làm nội dung gì để bán công cụ AI?</h2>
<ul><li><b>Video "dùng thử thật"</b>: quay màn hình làm một việc cụ thể bằng công cụ (viết bài, làm video, tạo ảnh).</li>
<li><b>So sánh 2 công cụ</b>: "X hay Y tốt hơn cho việc Z" — người xem đã sắp quyết định mua.</li>
<li><b>Danh sách công cụ theo nghề</b>: "5 công cụ AI cho người bán hàng online", "cho giáo viên", "cho YouTuber".</li></ul>
<p>Xem toàn bộ <a href="{ctx['u']('categories/ai/')}">chương trình Affiliate AI</a> được xếp hạng mỗi ngày.</p>"""
    faq = [("Làm Affiliate công cụ AI có khó không?", "Không khó nếu bạn thật sự dùng thử và chỉ cho người xem cách làm một việc cụ thể. Chọn chương trình duyệt tự động để bắt đầu ngay."),
           ("Hoa hồng công cụ AI thường bao nhiêu?", "Phần lớn từ 20% đến 50%, nhiều chương trình trả định kỳ 12 tháng hoặc trọn đời.")]
    return than, faq


BAI_VI = [
    {"slug": "hoa-hong-dinh-ky-tron-doi", "ham": bai_tron_doi, "anh": "assets/vi/bia-affiliate.webp",
     "tieu": "Top 10 sản phẩm Affiliate trả hoa hồng định kỳ trọn đời đáng làm nhất",
     "mota": "Danh sách sản phẩm Affiliate trả hoa hồng hằng tháng trọn đời, xếp hạng theo hoa hồng, cookie và điều khoản. Cập nhật mỗi ngày."},
    {"slug": "cach-chon-san-pham-affiliate", "ham": bai_chon_san_pham, "anh": "assets/vi/bia-affiliate.webp",
     "tieu": "Cách chọn sản phẩm Affiliate “ngon”: 6 tiêu chí soi trong 5 phút",
     "mota": "6 tiêu chí chọn sản phẩm Affiliate ra tiền: hoa hồng, cookie, xác minh, duyệt, nhận tiền và luật cấm — kèm ví dụ thật."},
    {"slug": "lam-affiliate-quoc-te-tu-viet-nam", "ham": bai_tu_viet_nam, "anh": "assets/vi/bia-affiliate.webp",
     "tieu": "Làm Affiliate quốc tế từ Việt Nam: chọn sản phẩm, nhận tiền và tránh bị khoá",
     "mota": "Hướng dẫn người Việt làm Affiliate quốc tế: chương trình nào nhận, nhận tiền qua PayPal hay ngân hàng, 5 lỗi hay bị khoá tài khoản."},
    {"slug": "san-pham-ai-affiliate-cho-nguoi-moi", "ham": bai_ai_nguoi_moi, "anh": "assets/vi/bia-affiliate.webp",
     "tieu": "7 sản phẩm AI có chương trình Affiliate tốt nhất cho người mới",
     "mota": "7 công cụ AI có chương trình Affiliate duyệt tự động, hoa hồng định kỳ, phù hợp người mới bắt đầu. Xếp hạng mỗi ngày."},
]
