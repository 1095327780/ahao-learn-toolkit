// copy buttons + nav border on scroll
document.querySelectorAll(".doc .copy").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var text = btn.closest(".doc").querySelector("code").innerText;
    function done() {
      btn.textContent = "已复制"; btn.classList.add("done");
      setTimeout(function () { btn.textContent = "复制全文"; btn.classList.remove("done"); }, 1600);
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
var nav = document.querySelector(".nav");
function onScroll() { nav && nav.classList.toggle("scrolled", window.scrollY > 8); }
window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
