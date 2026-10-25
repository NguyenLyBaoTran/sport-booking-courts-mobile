(function () {
  "use strict";

  var config = window.ManagementConfig || {};
  var baseUrl = String(config.apiBaseUrl || "http://localhost:8000").replace(/\/+$/, "");
  var tokenKey = "managementAccessToken";

  function readToken() {
    try { return window.sessionStorage.getItem(tokenKey) || ""; }
    catch (error) { return ""; }
  }

  function setToken(token) {
    window.sessionStorage.setItem(tokenKey, token);
  }

  function clearToken() {
    window.sessionStorage.removeItem(tokenKey);
  }

  function errorMessage(detail, fallback) {
    if (Array.isArray(detail)) {
      return detail.map(function (item) {
        var location = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
        return (location ? location + ": " : "") + (item.msg || "Invalid value");
      }).join("; ");
    }
    if (detail && typeof detail === "object") return JSON.stringify(detail);
    return detail === undefined || detail === null || detail === "" ? fallback : String(detail);
  }

  function ApiError(status, detail, fallback) {
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.message = errorMessage(detail, fallback);
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  function request(path, options) {
    var settings = options || {};
    var headers = { Accept: "application/json" };
    var token = settings.auth === false ? "" : readToken();
    if (token) headers.Authorization = "Bearer " + token;
    var requestOptions = { method: settings.method || "GET", headers: headers };
    if (settings.body !== undefined) {
      headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(settings.body);
    }
    return window.fetch(baseUrl + path, requestOptions).then(function (response) {
      if (response.status === 204) return null;
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          if (response.status === 401 && path !== "/api/v1/auth/login") {
            window.dispatchEvent(new window.CustomEvent("management:unauthorized"));
          }
          throw new ApiError(response.status, body.detail, response.status + " " + response.statusText);
        }
        return body;
      });
    }).catch(function (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, error && error.message, "Could not connect to the API Gateway.");
    });
  }

  window.CourtApi = {
    baseUrl: baseUrl,
    ApiError: ApiError,
    get: function (path) { return request(path); },
    post: function (path, body, authenticated) { return request(path, { method: "POST", body: body, auth: authenticated !== false }); },
    put: function (path, body) { return request(path, { method: "PUT", body: body }); },
    delete: function (path) { return request(path, { method: "DELETE" }); },
    login: function (email, password) {
      return request("/api/v1/auth/login", { method: "POST", body: { email: email, password: password }, auth: false });
    },
    setAccessToken: setToken,
    clearAccessToken: clearToken,
    hasAccessToken: function () { return !!readToken(); }
  };
})();
