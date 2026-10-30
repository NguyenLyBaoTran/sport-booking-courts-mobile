const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../assets/js/app.js"), "utf8");

function section(startText, endText) {
  const start = source.indexOf(startText);
  const end = source.indexOf(endText, start);
  assert.notEqual(start, -1, `missing section: ${startText}`);
  assert.notEqual(end, -1, `missing end: ${endText}`);
  return source.slice(start, end);
}

test("API Mode does not present Admin booking or check-in mocks as live data", () => {
  const bookings = section("  function bookingPage(active, admin)", "  function filteredDemoBookings()");
  const checkins = section("  function checkinPage(active, admin)", "  function checkDemoQr(");

  assert.match(bookings, /if \(dataMode !== "demo"\)[\s\S]*System-wide booking management is not available yet/);
  assert.match(bookings, /var adminRows = bookingRows\(true\)/);
  assert.match(checkins, /if \(dataMode !== "demo"\)[\s\S]*System-wide check-in history is not available yet/);
  assert.match(checkins, /var adminRows = data\.checkins/);
});

test("API Mode Admin dashboard marks unavailable summaries without sample totals", () => {
  const dashboard = section("  function dashboard(active)", "  function anyAdminDataError(resources)");

  assert.match(dashboard, /\["—", "—", "—", "—"\]/);
  assert.match(dashboard, /Account and booking summaries are not available yet/);
  assert.match(dashboard, /dataMode === "demo" \? '<p class="text-secondary small">Sample totals/);
});

test("API Mode Admin Users and Owner Revenue show unavailable states while Demo remains available", () => {
  const people = section("  function peoplePage()", "  function profilePage(");
  const revenue = section("  function revenuePage()", "  function peoplePage()");

  assert.match(people, /if \(dataMode !== "demo"\)[\s\S]*Account management is not available yet/);
  assert.match(people, /var rows = data\.people/);
  assert.match(revenue, /if \(dataMode !== "demo"\)[\s\S]*Revenue information is not available yet/);
  assert.match(revenue, /var values = \[42, 61/);
});

test("Login copy is concise and does not reveal test credentials or implementation details", () => {
  const login = section("  function renderLogin()", "  function renderShell(");

  assert.match(login, /Access your management workspace/);
  assert.match(login, /Sign in/);
  assert.doesNotMatch(login, /JWT|API Gateway|User Service|name@example\.com.{0,100}password/i);
  assert.doesNotMatch(login, /@example\.test|password123|admin@sportbooking/);
});

test("Admin data-source selector remains available on screens with separate Demo and live states", () => {
  assert.match(source, /var adminModeScreens = \["admin-dashboard", "admin-venues", "admin-schedule", "admin-bookings", "checkins", "people"\]/);
  assert.match(source, /if \(admin && adminModeScreens\.indexOf\(active\) >= 0\) content = modeToolbar\(\) \+ content/);
  assert.match(source, /authUser\.role === "ADMIN" && \["sports", "venues", "courts", "slots"\]/);
  assert.match(source, /authUser\.role === "OWNER" && resource !== "sports"/);
});
