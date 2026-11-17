const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

function loadAuthUtils() {
  const window = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/auth-utils.js"), "utf8"), { window, globalThis: {} });
  return window.ManagementAuthUtils;
}

test("Management authentication is API-only and never enables a Demo workspace", () => {
  const auth = loadAuthUtils();
  assert.equal(auth.normalizeMode("API"), "api");
  assert.equal(auth.normalizeMode("demo"), "api");
  assert.equal(auth.workspaceVisible("demo"), false);
  assert.equal(auth.workspaceVisible("api"), false);
  const api = auth.loginPlan("api", "ADMIN", "owner@example.test", "password");
  assert.equal(api.valid, true);
  assert.equal(api.mode, "api");
  assert.equal(api.sendsRequest, true);
  assert.equal(api.role, undefined);
});

test("Login always validates real API credentials", () => {
  const auth = loadAuthUtils();
  assert.match(auth.loginPlan("api", "OWNER", "bad-email", "x").message, /valid email/i);
  assert.match(auth.loginPlan("api", "OWNER", "owner@example.test", "").message, /password/i);
  assert.equal(auth.loginPlan("demo", "ADMIN", "", "").valid, false);
});

test("only OWNER and ADMIN receive management workspace routes", () => {
  const auth = loadAuthUtils();
  assert.equal(auth.homeRouteForRole("OWNER"), "dashboard");
  assert.equal(auth.homeRouteForRole("ADMIN"), "admin-dashboard");
  assert.equal(auth.homeRouteForRole("USER"), null);
  assert.equal(auth.homeRouteForRole(undefined), null);
});

test("login utilities load before app code and changed assets use a cache version", () => {
  const html = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
  assert.doesNotMatch(html, /data\.js|court-demo-data|booking-demo-data/);
  assert.ok(html.indexOf("assets/js/auth-utils.js?v=") < html.indexOf("assets/js/app.js?v="));
  assert.match(html, /assets\/css\/app\.css\?v=/);
});
