const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../assets/js/admin-api.js"), "utf8");

function loadApi() {
  const calls = [];
  const window = {
    CourtApi: {
      get: (url) => { calls.push({ method: "GET", url }); return Promise.resolve({ items: [], total: 0, page: 1, page_size: 25 }); },
      patch: (url, body) => { calls.push({ method: "PATCH", url, body }); return Promise.resolve({ is_active: body.is_active }); }
    }
  };
  vm.runInNewContext(source, { window, URLSearchParams });
  return { api: window.AdminManagementApi, calls };
}

test("Admin user list serializes supported filters and pagination", async () => {
  const { api, calls } = loadApi();
  const result = await api.listUsers({ page: 2, page_size: 25, q: "Owner", role: "OWNER", is_active: false });
  assert.equal(result.total, 0);
  assert.equal(calls[0].method, "GET");
  assert.equal(calls[0].url, "/api/v1/admin/users?page=2&page_size=25&q=Owner&role=OWNER&is_active=false");
});

test("Admin booking and check-in lists use distinct read-only endpoints", async () => {
  const { api, calls } = loadApi();
  await api.listBookings({ page: 1, page_size: 25, status: "CHECKED_IN", date_from: "2026-10-01" });
  await api.listCheckins({ page: 1, page_size: 25, booking_id: 42 });
  assert.equal(calls[0].url, "/api/v1/admin/bookings?page=1&page_size=25&status=CHECKED_IN&date_from=2026-10-01");
  assert.equal(calls[1].url, "/api/v1/admin/checkins?page=1&page_size=25&booking_id=42");
});

test("Admin booking search can target either a booking ID or supported customer ID filter", async () => {
  const { api, calls } = loadApi();
  await api.listBookings({ page: 1, page_size: 25, booking_id: "42" });
  await api.listBookings({ page: 1, page_size: 25, user_id: "8" });
  assert.equal(calls[0].url, "/api/v1/admin/bookings?page=1&page_size=25&booking_id=42");
  assert.equal(calls[1].url, "/api/v1/admin/bookings?page=1&page_size=25&user_id=8");
});

test("User detail and status update use the safe Admin routes", async () => {
  const { api, calls } = loadApi();
  await api.getUser("u/42");
  await api.setUserActive(42, false);
  assert.equal(calls[0].url, "/api/v1/admin/users/u%2F42");
  assert.equal(calls[1].method, "PATCH");
  assert.equal(calls[1].url, "/api/v1/admin/users/42/status");
  assert.equal(calls[1].body.is_active, false);
});

test("Admin list client rejects an unpaginated or malformed response", async () => {
  const window = { CourtApi: { get: () => Promise.resolve([]) } };
  vm.runInNewContext(source, { window, URLSearchParams });
  await assert.rejects(window.AdminManagementApi.listBookings({}), /unexpected paginated response/);
});
