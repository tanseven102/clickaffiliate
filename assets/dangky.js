// Form đăng ký nhận bản tin — ghi email vào Supabase (bảng chỉ cho ghi, không ai đọc được từ trình duyệt)
(function () {
  const URL_DB = "https://idnfafxgrbabypfokgve.supabase.co/rest/v1/clickaffiliate_subscribers";
  const KHOA = "sb_publishable_Subrht5w8KLv8WC95UbriQ_XlO8QNYW";
  document.querySelectorAll("form.dk-form").forEach((f) => {
    f.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const btn = f.querySelector("button"), tb = f.querySelector(".dk-tb");
      const email = f.email.value.trim().toLowerCase();
      if (f.website && f.website.value) return; // bẫy máy spam
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { tb.textContent = "Please enter a valid email."; tb.className = "dk-tb loi"; return; }
      const chon = [...f.querySelectorAll("input[name=interest]:checked")].map((x) => x.value).join(",").slice(0, 200);
      btn.disabled = true; tb.textContent = "Subscribing…"; tb.className = "dk-tb";
      try {
        const r = await fetch(URL_DB, {
          method: "POST",
          headers: { apikey: KHOA, "Content-Type": "application/json", Prefer: "return=minimal" },
          body: JSON.stringify({ email, source: (f.dataset.src || location.pathname).slice(0, 120), interests: chon || null }),
        });
        if (r.ok || r.status === 409) {
          f.innerHTML = '<div class="dk-xong">✓ You\'re in! Watch your inbox for the next ClickAffiliate Weekly.</div>';
          try { localStorage.setItem("ca_dk", "1"); } catch (e) {}
        } else throw new Error(r.status);
      } catch (e) {
        tb.textContent = "Something went wrong. Please try again."; tb.className = "dk-tb loi"; btn.disabled = false;
      }
    });
  });
})();
