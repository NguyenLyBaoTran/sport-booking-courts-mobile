(function () {
  "use strict";

  var script = document.createElement("script");
  script.src = new URL("../vendor/html5-qrcode-2.3.8.min.js", document.currentScript.src).href;
  script.async = true;
  script.onload = function () { document.dispatchEvent(new CustomEvent("qrscannerloaded")); };
  script.onerror = function () {
    window.Html5QrcodeLoadError = "The local html5-qrcode library could not be loaded. Reload the page or check the Management Web files.";
    document.dispatchEvent(new CustomEvent("qrscannerloaderror"));
  };
  document.head.appendChild(script);
})();
