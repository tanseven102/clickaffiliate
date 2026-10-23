// Bộ lọc thư mục chương trình — đọc data/programs.json, lọc + sắp xếp ngay trên trình duyệt
(function () {
  const B = window.CA_BASE || "";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let all = [], shown = 50;

  const logo = (p) => {
    const ch = esc(p.n.slice(0, 1).toUpperCase());
    return p.dm
      ? `<img class="logo" loading="lazy" width="34" height="34" alt="" src="https://www.google.com/s2/favicons?domain=${esc(p.dm)}&sz=64" onerror="this.outerHTML='<span class=chu-cai>${ch}</span>'">`
      : `<span class="chu-cai">${ch}</span>`;
  };
  const row = (p, i) => `<tr><td class="so${i <= 3 ? " top3" : ""}">#${i}</td>
<td><a class="ten" href="${B}/programs/${p.s}/">${logo(p)}<span><b>${esc(p.n)}</b>${p.ok ? ' <span class="pill ok">✓ verified</span>' : ""}${p.x ? ' <span class="pill do">paused</span>' : ""}<small>${esc(p.d)}</small></span></a></td>
<td>${esc(p.r)}</td><td class="an-mobile">${p.k ? p.k + " days" : "—"}</td>
<td class="an-mobile"><a class="pill xanh" href="${B}/categories/${p.cs}/">${esc(p.c)}</a></td>
<td><span class="diem">${p.sc}<i class="g-${p.g.replace("+", "p")}">${p.g}</i></span></td></tr>`;

  function render() {
    const q = $("q").value.trim().toLowerCase(), cat = $("cat").value, typ = $("typ").value, ver = $("ver").checked, s = $("sort").value;
    let l = all.filter((p) =>
      (!q || (p.n + " " + p.d + " " + p.c).toLowerCase().includes(q)) &&
      (!cat || p.c === cat) &&
      (!typ || (typ === "hybrid" ? p.t === "hybrid" || p.t === "tiered" : p.t === typ)) &&
      (!ver || p.ok));
    const by = { sc: (a, b) => b.sc - a.sc, v: (a, b) => b.v - a.v, k: (a, b) => b.k - a.k, a: (a, b) => b.a.localeCompare(a.a), n: (a, b) => a.n.localeCompare(b.n) }[s];
    l.sort(by);
    $("dem").textContent = `${l.length.toLocaleString()} programs`;
    $("ds").innerHTML = `<div class="card bang-cuon"><table class="rank"><thead><tr><th>#</th><th>Program</th><th>Commission</th><th class="an-mobile">Cookie</th><th class="an-mobile">Category</th><th>ClickScore</th></tr></thead><tbody>${l.slice(0, shown).map((p, i) => row(p, i + 1)).join("")}</tbody></table></div>`;
    $("them").hidden = l.length <= shown;
    const url = new URL(location.href);
    q ? url.searchParams.set("q", q) : url.searchParams.delete("q");
    cat ? url.searchParams.set("cat", cat) : url.searchParams.delete("cat");
    history.replaceState(null, "", url);
  }

  fetch(`${B}/data/programs.json`).then((r) => r.json()).then((d) => {
    all = d;
    const sp = new URLSearchParams(location.search);
    if (sp.get("q")) $("q").value = sp.get("q");
    if (sp.get("cat")) $("cat").value = sp.get("cat");
    ["q", "cat", "typ", "sort", "ver"].forEach((id) => $(id).addEventListener("input", () => { shown = 50; render(); }));
    $("them").addEventListener("click", () => { shown += 100; render(); });
    render();
  });
})();
