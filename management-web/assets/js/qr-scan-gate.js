(function (root) {
  "use strict";

  function createQrScanGate() {
    var pending = false;
    var lastToken = "";

    return {
      tryBegin: function (token) {
        var normalized = String(token || "").trim();
        if (!normalized || pending || normalized === lastToken) return false;
        pending = true;
        lastToken = normalized;
        return true;
      },
      finish: function () {
        pending = false;
      },
      reset: function () {
        pending = false;
        lastToken = "";
      },
      isPending: function () {
        return pending;
      }
    };
  }

  root.QrScanGate = { create: createQrScanGate };
})(window);
