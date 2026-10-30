(function () {
  "use strict";

  function queryString(values) {
    var query = new URLSearchParams();
    Object.keys(values || {}).forEach(function (key) {
      var value = values[key];
      if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    });
    var encoded = query.toString();
    return encoded ? "?" + encoded : "";
  }

  function list(path, filters) {
    return window.CourtApi.get(path + queryString(filters)).then(function (result) {
      if (!result || !Array.isArray(result.items) || !Number.isInteger(result.total) ||
          !Number.isInteger(result.page) || !Number.isInteger(result.page_size)) {
        throw new Error("The Admin API returned an unexpected paginated response.");
      }
      return result;
    });
  }

  window.AdminManagementApi = {
    listUsers: function (filters) { return list("/api/v1/admin/users", filters); },
    getUser: function (id) { return window.CourtApi.get("/api/v1/admin/users/" + encodeURIComponent(id)); },
    setUserActive: function (id, isActive) {
      return window.CourtApi.patch("/api/v1/admin/users/" + encodeURIComponent(id) + "/status", { is_active: !!isActive });
    },
    listBookings: function (filters) { return list("/api/v1/admin/bookings", filters); },
    getBooking: function (id) { return window.CourtApi.get("/api/v1/admin/bookings/" + encodeURIComponent(id)); },
    listCheckins: function (filters) { return list("/api/v1/admin/checkins", filters); }
  };
})();
