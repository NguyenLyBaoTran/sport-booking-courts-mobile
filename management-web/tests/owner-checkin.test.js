const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.join(__dirname, "../assets/js");
const appSource = fs.readFileSync(path.join(root, "app.js"), "utf8");

function createClient(fetchImpl) {
  const values = new Map();
  const events = [];
  class CustomEvent { constructor(type) { this.type = type; } }
  const window = {
    ManagementConfig: { apiBaseUrl: "http://gateway.test" },
    sessionStorage: {
      getItem: (key) => values.get(key) || null,
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key)
    },
    fetch: fetchImpl,
    CustomEvent,
    dispatchEvent: (event) => events.push(event.type)
  };
  const context = { window };
  vm.runInNewContext(fs.readFileSync(path.join(root, "api.js"), "utf8"), context);
  vm.runInNewContext(fs.readFileSync(path.join(root, "owner-checkin-api.js"), "utf8"), context);
  return { api: window.CourtApi, checkin: window.OwnerCheckinApi, events };
}

function response(status, body) {
  return { status, ok: status >= 200 && status < 300, statusText: "", json: async () => body };
}

test("Owner check-in POST sends only qr_token and the session Bearer JWT", async () => {
  let request;
  const client = createClient(async (url, options) => {
    request = { url, options };
    return response(200, { booking_id: 42, status: "CHECKED_IN", checked_in_at: "2026-10-29T10:00:00Z" });
  });
  client.api.setAccessToken("owner-jwt");
  const token = "opaque-qr-token";
  const result = await client.checkin.checkIn(token);
  assert.equal(request.url, "http://gateway.test/api/v1/owner/checkins");
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Authorization, "Bearer owner-jwt");
  assert.equal(request.options.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(request.options.body), { qr_token: token });
  assert.equal(Object.hasOwn(JSON.parse(request.options.body), "owner_id"), false);
  assert.equal(Object.hasOwn(request.options.headers, "X-Internal-Token"), false);
  assert.equal(result.status, "CHECKED_IN");
});

test("blank manual tokens are rejected without a request", async () => {
  let calls = 0;
  const client = createClient(async () => { calls += 1; return response(200, {}); });
  await assert.rejects(client.checkin.checkIn("  "), /Enter a QR token/);
  assert.equal(calls, 0);
});

test("check-in helper preserves API error statuses and does not expose request token", async () => {
  for (const status of [401, 403, 404, 409, 422, 503, 504]) {
    const client = createClient(async () => response(status, { detail: "upstream diagnostic" }));
    try {
      await client.checkin.checkIn("private-token");
      assert.fail("expected request to fail");
    } catch (error) {
      assert.equal(error.status, status);
      assert.equal(error.message.includes("private-token"), false);
    }
  }
});

test("scanner supports API and Demo modes without token display or mock fallback", () => {
  assert.match(appSource, /new window\.Html5Qrcode\("qr-reader"\)/);
  assert.match(appSource, /data-scanner-start/);
  assert.match(appSource, /data-scanner-stop/);
  assert.match(appSource, /submitOwnerCheckin\(decodedText\)/);
  assert.match(appSource, /window\.OwnerCheckinApi\.checkIn\(qrToken\)/);
  assert.match(appSource, /data-owner-qr-submit/);
  assert.match(appSource, /data-demo-qr-submit/);
  assert.match(appSource, /Camera permission was denied/);
  assert.match(appSource, /No camera was found/);
  assert.match(appSource, /if \(scanProcessing \|\| \(decodedText === lastScannedText/);
  assert.match(appSource, /if \(qrScanner && dataMode !== "demo"\) stopQrScanner\(\)/);
  assert.match(appSource, /window\.addEventListener\("hashchange"/);
  assert.match(appSource, /renderedRoute === "qr-checkin" && nextRoute !== "qr-checkin"/);
  assert.match(appSource, /dataMode === "demo"\) \{ checkDemoQr\(qrToken\)/);
  assert.match(appSource, /No sample token is used/);
  assert.match(appSource, /ownerBookingsState\.status = "idle"/);
  for (const status of [401, 403, 404, 409, 422, 503, 504]) assert.match(appSource, new RegExp("status === " + status));
  assert.doesNotMatch(appSource, /console\.(log|debug|info)\([^\n]*qrToken/i);
});
