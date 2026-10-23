(function () {
  "use strict";

  var config = window.ManagementConfig || {};
  var baseUrl = String(config.apiBaseUrl || "http://localhost:8000").replace(/\/+$/, "");

  function get(path) {
    return fetch(baseUrl + path, {
      method: "GET",
      headers: { Accept: "application/json" }
    }).then(function (response) {
      if (!response.ok) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          var message = body.detail || (response.status + " " + response.statusText);
          throw new Error(String(message));
        });
      }
      return response.json();
    });
  }

  window.CourtApi = { get: get, baseUrl: baseUrl };
})();
