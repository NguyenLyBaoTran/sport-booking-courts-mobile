(function () {
  "use strict";

  function list(filters) {
    var query = new URLSearchParams();
    ["venue_id", "date", "status"].forEach(function (key) {
      if (filters && filters[key]) query.set(key, filters[key]);
    });
    var suffix = query.toString();
    return window.CourtApi.get("/api/v1/owner/bookings" + (suffix ? "?" + suffix : ""));
  }

  function detail(bookingId) {
    return window.CourtApi.get("/api/v1/owner/bookings/" + encodeURIComponent(bookingId));
  }

  function complete(bookingId) {
    return window.CourtApi.post("/api/v1/owner/bookings/" + encodeURIComponent(bookingId) + "/complete", undefined);
  }

  window.OwnerBookingsApi = { list: list, detail: detail, complete: complete };
})();
