const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

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
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/api.js"), "utf8"), { window });
  return { api: window.CourtApi, calls: events };
}

function response(status, body, statusText = "") {
  return {
    status,
    ok: status >= 200 && status < 300,
    statusText,
    json: async () => body
  };
}

test("attaches the session Bearer token to Court API requests", async () => {
  let request;
  const { api } = createClient(async (_url, options) => {
    request = options;
    return response(200, []);
  });
  api.setAccessToken("test-token");
  await api.get("/api/v1/venues");
  assert.equal(request.headers.Authorization, "Bearer test-token");
});

test("login sends JSON credentials without an existing Bearer token", async () => {
  let request;
  const { api } = createClient(async (_url, options) => {
    request = options;
    return response(200, { access_token: "issued-token" });
  });
  api.setAccessToken("old-token");
  await api.login("owner@example.test", "password");
  assert.equal(request.method, "POST");
  assert.equal(request.headers["Content-Type"], "application/json");
  assert.equal(request.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(request.body), { email: "owner@example.test", password: "password" });
});

test("logout can clear the stored API access token", () => {
  const { api } = createClient(async () => response(200, {}));
  api.setAccessToken("session-token");
  assert.equal(api.hasAccessToken(), true);
  api.clearAccessToken();
  assert.equal(api.hasAccessToken(), false);
});

test("expired or invalid session dispatches the unauthorized event", async () => {
  const { api, calls } = createClient(async () => response(401, { detail: "Not authenticated" }, "Unauthorized"));
  api.setAccessToken("expired-token");
  await assert.rejects(api.get("/api/v1/users/me"), (error) => error.status === 401);
  assert.deepEqual(calls, ["management:unauthorized"]);
});

test("login failures do not trigger the expired-session handler", async () => {
  const { api, calls } = createClient(async () => response(401, { detail: "Invalid email or password" }, "Unauthorized"));
  await assert.rejects(api.login("owner@example.test", "wrong-password"), (error) => error.status === 401);
  assert.deepEqual(calls, []);
});

test("formats FastAPI validation errors", async () => {
  const { api } = createClient(async () => response(422, { detail: [{ loc: ["body", "start_time"], msg: "invalid time" }] }, "Unprocessable Entity"));
  await assert.rejects(api.post("/api/v1/time-slots", {}), (error) => error.status === 422 && error.message === "start_time: invalid time");
});

test("preserves conflict status and detail for overlap feedback", async () => {
  const { api } = createClient(async () => response(409, { detail: "Time slot overlaps an active slot" }, "Conflict"));
  await assert.rejects(api.post("/api/v1/time-slots", {}), (error) => error.status === 409 && error.message === "Time slot overlaps an active slot");
});

test("204 soft-delete response resolves without parsing a body", async () => {
  const { api } = createClient(async () => response(204, null));
  assert.equal(await api.delete("/api/v1/venues/5"), null);
});
