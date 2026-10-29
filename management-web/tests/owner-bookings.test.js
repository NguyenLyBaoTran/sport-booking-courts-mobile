const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const appSource = fs.readFileSync(path.join(__dirname, "../assets/js/app.js"), "utf8");

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
  const context = { window, URLSearchParams, encodeURIComponent };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/api.js"), "utf8"), context);
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/owner-bookings-api.js"), "utf8"), context);
  return { api: window.CourtApi, bookings: window.OwnerBookingsApi, events };
}

function response(status, body, statusText = "") {
  return {
    status,
    ok: status >= 200 && status < 300,
    statusText,
    json: async () => body
  };
}

test("Owner booking list fetches the approved filters and sends the Bearer JWT", async () => {
  let captured;
  const { api, bookings } = createClient(async (url, options) => {
    captured = { url, options };
    return response(200, [{ id: 42, venue_id: 12, status: "CONFIRMED" }]);
  });
  api.setAccessToken("owner-session-token");

  const rows = await bookings.list({ venue_id: "12", date: "2026-10-29", status: "CONFIRMED" });

  assert.equal(rows[0].id, 42);
  assert.equal(captured.url, "http://gateway.test/api/v1/owner/bookings?venue_id=12&date=2026-10-29&status=CONFIRMED");
  assert.equal(captured.options.method, "GET");
  assert.equal(captured.options.headers.Authorization, "Bearer owner-session-token");
});

test("Owner booking list omits empty filters and does not assume pagination", async () => {
  let requestedUrl;
  const { bookings } = createClient(async (url) => {
    requestedUrl = url;
    return response(200, []);
  });

  assert.deepEqual(await bookings.list({ venue_id: "", date: "", status: "" }), []);
  assert.equal(requestedUrl, "http://gateway.test/api/v1/owner/bookings");
});

test("Owner booking detail uses the approved detail endpoint", async () => {
  let requestedUrl;
  const { bookings } = createClient(async (url) => {
    requestedUrl = url;
    return response(200, { id: 42, venue_id: 12, court_id: 4, status: "CHECKED_IN" });
  });

  const detail = await bookings.detail(42);

  assert.equal(detail.status, "CHECKED_IN");
  assert.equal(requestedUrl, "http://gateway.test/api/v1/owner/bookings/42");
});

test("Owner booking completion sends a bodyless POST", async () => {
  let captured;
  const { api, bookings } = createClient(async (url, options) => {
    captured = { url, options };
    return response(200, { booking_id: 42, status: "COMPLETED", completed_at: "2026-10-29T12:00:00Z" });
  });
  api.setAccessToken("owner-session-token");

  const result = await bookings.complete(42);

  assert.equal(result.status, "COMPLETED");
  assert.equal(captured.url, "http://gateway.test/api/v1/owner/bookings/42/complete");
  assert.equal(captured.options.method, "POST");
  assert.equal(captured.options.body, undefined);
  assert.equal(captured.options.headers.Authorization, "Bearer owner-session-token");
});

test("Owner booking API helper preserves 401/403/404/409/422/503/504 statuses", async () => {
  for (const status of [401, 403, 404, 409, 422, 503, 504]) {
    const { bookings } = createClient(async () => response(status, { detail: "upstream detail" }, "Upstream error"));
    await assert.rejects(bookings.list({}), (error) => error.status === status);
  }
});

test("Owner API Mode renders only contract fields, with loading, empty, filtered, and error states", () => {
  const start = appSource.indexOf('    if (dataMode !== "demo") {', appSource.indexOf("  function bookingPage("));
  const end = appSource.indexOf("    var filtered = filteredDemoBookings();", start);
  const apiBranch = appSource.slice(start, end);
  assert.match(apiBranch, /Loading bookings/);
  assert.match(apiBranch, /No bookings are available for your venues/);
  assert.match(apiBranch, /No bookings match these filters/);
  assert.match(apiBranch, /ownerBookingErrorMessage\(ownerBookingsState\.error\)/);
  assert.match(apiBranch, /data-booking-venue/);
  assert.match(apiBranch, /Filter booking date/);
  assert.match(apiBranch, /data-booking-status/);
  assert.doesNotMatch(apiBranch, /demoBookings|booking\.customer|qr_token/);
});

test("API list requests use venue/date/status filters and no mock fallback", () => {
  assert.match(appSource, /OwnerBookingsApi\.list\(\{ venue_id: bookingVenueId, date: bookingDate, status: bookingStatus \}\)/);
  assert.match(appSource, /if \(dataMode === "demo" \|\| !authUser \|\| authUser\.role !== "OWNER"\) return Promise\.resolve\(\[\]\)/);
  assert.match(appSource, /ownerBookingsState = \{ status: "error", data: \[\], error: error \}/);
  assert.doesNotMatch(appSource, /ownerBookingsState\.error[\s\S]{0,150}demoBookings/);
});

test("API booking detail uses only API fields and omits qr_token", () => {
  const start = appSource.indexOf("  function bookingDetail(booking) {");
  const end = appSource.indexOf("  function showManagedModal(", start);
  const detail = appSource.slice(start, end);
  const detailLoaderStart = appSource.indexOf("  function loadOwnerBookingDetail(");
  const detailLoaderEnd = appSource.indexOf("  function refreshOwnerBookingAfterCompletion(", detailLoaderStart);
  assert.match(appSource.slice(detailLoaderStart, detailLoaderEnd), /OwnerBookingsApi\.detail/);
  assert.match(detail, /booking\.user_id/);
  assert.match(detail, /booking\.venue_id/);
  assert.match(detail, /booking\.court_id/);
  assert.match(detail, /booking\.time_slot_id/);
  assert.doesNotMatch(detail, /qr_token/);
  assert.match(detail, /apiBooking \? \[\["User ID", booking\.user_id\]\]/);
  assert.match(detail, /if \(!apiBooking && booking\.customer\.email\)/);
});

test("Completion is CHECKED_IN-only, confirmed, non-optimistic, and refreshes list and detail", () => {
  const start = appSource.indexOf("  function completeOwnerBooking(");
  const end = appSource.indexOf("  function bookingDetail(", start);
  const complete = appSource.slice(start, end);
  assert.match(complete, /booking\.status !== "CHECKED_IN"/);
  assert.match(complete, /window\.confirm\("Complete booking /);
  assert.match(complete, /OwnerBookingsApi\.complete\(booking\.id\)/);
  assert.match(complete, /refreshOwnerBookingAfterCompletion\(booking\.id\)/);
  assert.match(complete, /error\.status === 409/);
  assert.doesNotMatch(complete, /booking\.status\s*=\s*"COMPLETED"/);
});

test("API errors show safe user-facing messages for the contract statuses", () => {
  const start = appSource.indexOf("  function ownerBookingErrorMessage(");
  const end = appSource.indexOf("  function loadOwnerBookingDetail(", start);
  const messages = appSource.slice(start, end);
  for (const status of [401, 403, 404, 409, 422, 503, 504, 0]) {
    assert.match(messages, new RegExp("status === " + status));
  }
  assert.doesNotMatch(messages, /error\.detail|error\.message/);
});

test("Demo Mode retains mock rows and local-only completion behavior", () => {
  const demoData = fs.readFileSync(path.join(__dirname, "../assets/js/booking-demo-data.js"), "utf8");
  const start = appSource.indexOf("  function completeDemoBooking(");
  const end = appSource.indexOf("  function venuePage(", start);
  const complete = appSource.slice(start, end);
  assert.match(demoData, /demo-qr-checked-in-3105/);
  assert.match(appSource, /var filtered = filteredDemoBookings\(\)/);
  assert.match(complete, /dataMode !== "demo"\) \{ toast\(/);
  assert.match(complete, /Demo booking completed\. No API request was sent/);
});
