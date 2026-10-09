// copy buttons, expand/collapse, tabs, nav border on scroll
document.querySelectorAll(".doc .copy").forEach(function (btn) {
  var label = btn.textContent;
  btn.addEventListener("click", function () {
    var text = btn.closest(".doc").querySelector("code").innerText;
    function done() {
      btn.textContent = "已复制"; btn.classList.add("done");
      setTimeout(function () { btn.textContent = label; btn.classList.remove("done"); }, 1600);
    }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { btn.textContent = "请长按选择复制"; }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  });
});
document.querySelectorAll(".doc .expand").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var doc = btn.closest(".doc");
    var collapsed = doc.classList.toggle("is-collapsed");
    btn.textContent = collapsed ? btn.dataset.more : btn.dataset.less;
  });
});
document.querySelectorAll(".tool-panel").forEach(function (panel) {
  var tabs = panel.querySelectorAll(".tab");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        panel.querySelector("#" + t.dataset.tab).hidden = !on;
      });
    });
  });
});
var nav = document.querySelector(".nav");
function onScroll() { nav && nav.classList.toggle("scrolled", window.scrollY > 8); }
window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
