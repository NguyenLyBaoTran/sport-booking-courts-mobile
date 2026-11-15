(function (root) {
  "use strict";

  function normalizeMode(mode) {
    return "api";
  }

  function workspaceVisible(mode) {
    return false;
  }

  function loginPlan(mode, workspace, email, password) {
    var normalizedEmail = String(arguments.length >= 4 ? email : mode || "").trim();
    var passwordValue = arguments.length >= 4 ? password : workspace;
    var emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail);
    if (!emailValid) return { valid: false, mode: "api", message: "Enter a valid email address." };
    if (!String(passwordValue || "")) return { valid: false, mode: "api", message: "Enter your password." };
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
