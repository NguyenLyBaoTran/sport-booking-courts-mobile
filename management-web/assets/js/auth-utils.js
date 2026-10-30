(function (root) {
  "use strict";

  function normalizeMode(mode) {
    return String(mode || "").toLowerCase() === "api" ? "api" : "demo";
  }

  function workspaceVisible(mode) {
    return normalizeMode(mode) === "demo";
  }

  function loginPlan(mode, workspace, email, password) {
    if (normalizeMode(mode) === "demo") {
      var role = String(workspace || "").toUpperCase();
      if (role !== "OWNER" && role !== "ADMIN") return { valid: false, mode: "demo", message: "Choose a Demo workspace." };
      return { valid: true, mode: "demo", role: role, requiresCredentials: false, sendsRequest: false };
    }
    var normalizedEmail = String(email || "").trim();
    var emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail);
    if (!emailValid) return { valid: false, mode: "api", message: "Enter a valid email address." };
    if (!String(password || "")) return { valid: false, mode: "api", message: "Enter your password." };
    return { valid: true, mode: "api", requiresCredentials: true, sendsRequest: true };
  }

  function homeRouteForRole(role) {
    var normalizedRole = String(role || "").toUpperCase();
    if (normalizedRole === "OWNER") return "dashboard";
    if (normalizedRole === "ADMIN") return "admin-dashboard";
    return null;
  }

  root.ManagementAuthUtils = {
    normalizeMode: normalizeMode,
    workspaceVisible: workspaceVisible,
    loginPlan: loginPlan,
    homeRouteForRole: homeRouteForRole
  };
})(typeof window === "undefined" ? globalThis : window);
