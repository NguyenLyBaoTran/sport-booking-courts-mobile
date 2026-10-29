(function () {
  "use strict";

  function checkIn(qrToken) {
    var token = String(qrToken || "").trim();
    if (!token) return Promise.reject(new Error("Enter a QR token to continue."));
    return window.CourtApi.post("/api/v1/owner/checkins", { qr_token: token });
  }

  window.OwnerCheckinApi = { checkIn: checkIn };
})();
