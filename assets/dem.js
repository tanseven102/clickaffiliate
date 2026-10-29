// Đếm lượt vào ClickAffiliate — ghi 1 dòng vào Supabase (bảng chỉ cho ghi). Không cookie, không lưu IP.
(function () {
  try {
    if (navigator.webdriver || localStorage.getItem("ca_toi") === "1") return; // bỏ máy tự động + máy anh Tân
    let khach = localStorage.getItem("ca_khach");
    if (!khach) { khach = Math.random().toString(36).slice(2, 12); localStorage.setItem("ca_khach", khach); }
    const q = new URLSearchParams(location.search), go = location.pathname.indexOf("/go/") === 0;
    let ref = ""; try { ref = document.referrer ? new URL(document.referrer).hostname : ""; } catch (e) {}
    if (ref === location.hostname) ref = "";
    fetch("https://idnfafxgrbabypfokgve.supabase.co/rest/v1/clickaffiliate_views", {
      method: "POST", keepalive: true,
      headers: { apikey: "sb_publishable_Subrht5w8KLv8WC95UbriQ_XlO8QNYW", "Content-Type": "application/json", Prefer: "return=minimal" },
      body: JSON.stringify({ path: location.pathname.slice(0, 200), ref: ref.slice(0, 200) || null, k: (q.get("k") || "").slice(0, 60) || null,
        loai: go ? "go" : "xem", khach, lang: (navigator.language || "").slice(0, 20) }),
    }).catch(function () {});
  } catch (e) {}
})();
