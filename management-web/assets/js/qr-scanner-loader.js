(function () {
  "use strict";

  var script = document.createElement("script");
  script.src = "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";
  script.async = true;
  script.onload = function () { document.dispatchEvent(new CustomEvent("qrscannerloaded")); };
  script.onerror = function () {
    window.Html5QrcodeLoadError = "html5-qrcode CDN could not be loaded. Check network access and retry.";
    document.dispatchEvent(new CustomEvent("qrscannerloaderror"));
  };
  document.head.appendChild(script);
})();
