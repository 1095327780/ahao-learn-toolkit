document.querySelectorAll(".code .copy").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var text = btn.parentElement.querySelector("code").innerText;
    var done = function () { btn.textContent = "已复制"; setTimeout(function () { btn.textContent = "复制全文"; }, 1600); };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else { fallback(); }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { btn.textContent = "请长按选择复制"; }
      document.body.removeChild(ta);
    }
  });
});
