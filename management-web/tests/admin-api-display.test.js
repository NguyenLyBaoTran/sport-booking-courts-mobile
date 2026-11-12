const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../assets/js/app.js"), "utf8");
const styles = fs.readFileSync(path.join(__dirname, "../assets/css/app.css"), "utf8");

function section(startText, endText) {
  const start = source.indexOf(startText);
  const end = source.indexOf(endText, start);
  assert.notEqual(start, -1, `missing section: ${startText}`);
  assert.notEqual(end, -1, `missing end: ${endText}`);
  return source.slice(start, end);
}

test("Details modals use roomy two-column fields with stacked labels and values", () => {
  assert.match(source, /resource-details-grid/);
  assert.match(source, /admin-record-detail-modal/);
  assert.match(source, /record-details-grid/);
  assert.match(source, /booking-detail-grid/);
  assert.match(styles, /\.resource-details-grid, \.record-details-grid \{ display: grid; grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(styles, /\.booking-detail-grid \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(styles, /\.account-information-grid \.detail-row, \.resource-details-grid \.detail-row, \.record-details-grid \.detail-row, \.booking-detail-grid \.detail-row \{[^}]*flex-direction: column/);
  assert.match(styles, /\.detail-value--nowrap \{ white-space: nowrap; \}/);
  assert.match(styles, /\.modal \.modal-title\.fs-6 \{ font-size: 21px !important/);
  assert.match(styles, /overflow-wrap: break-word; word-break: normal/);
  assert.doesNotMatch(styles, /word-break:\s*break-all/);
  assert.match(styles, /\.booking-detail-modal \{ width: min\(760px, 100%\)/);
  assert.match(styles, /\.booking-detail-grid, \.resource-details-grid, \.record-details-grid \{ grid-template-columns: 1fr; \}/);
});

test("Admin API Mode uses paginated read-only booking and check-in endpoints without Demo fallback", () => {
  const bookings = section("  function bookingPage(active, admin)", "  function filteredDemoBookings()");
  const checkins = section("  function checkinPage(active, admin)", "  function checkDemoQr(");

  assert.match(source, /kind === "bookings" \? window\.AdminManagementApi\.listBookings/);
  assert.match(bookings, /data-admin-booking-detail/);
  assert.match(bookings, /System-wide booking records · read-only/);
  assert.doesNotMatch(bookings, /booking\.qr_token/);
  assert.match(bookings, /var adminRows = bookingRows\(true\)/);
  assert.match(source, /window\.AdminManagementApi\.listCheckins/);
  assert.match(checkins, /History recorded on bookings · read-only/);
  assert.match(checkins, /var adminRows = data\.checkins/);
});

test("Admin booking and check-in toolbars expose only supported, clearly named filters", () => {
  const bookings = section("  function bookingPage(active, admin)", "  function filteredDemoBookings()");
  const checkins = section("  function checkinPage(active, admin)", "  function checkDemoQr(");

  assert.match(bookings, /data-admin-booking-search-by/);
  assert.match(bookings, />Customer ID</);
  assert.match(bookings, /emptyLabel: "Date from"/);
  assert.match(bookings, /emptyLabel: "Date to"/);
  assert.doesNotMatch(bookings, /data-admin-booking-field|Venue ID|Court ID|Owner ID/);
  assert.match(checkins, /data-admin-checkin-booking/);
  assert.match(checkins, /emptyLabel: "Date from"/);
  assert.match(checkins, /emptyLabel: "Date to"/);
  assert.doesNotMatch(checkins, /data-admin-checkin-field|Owner ID|Court ID/);
});

test("Admin API errors distinguish missing list endpoints, missing records, server errors and network failures", () => {
  const handler = section("  function adminApiErrorMessage(error, context)", "  function loadAdminPage(kind, filters)");

  assert.match(handler, /context === "list"/);
  assert.match(handler, /error\.detail === "Not Found"/);
  assert.match(handler, /This Admin API is not available in the connected service yet/);
  assert.match(handler, /The requested record was not found/);
  assert.match(handler, /status >= 500/);
  assert.match(handler, /Could not connect to the API Gateway/);
  assert.match(source, /No records found\./);
  assert.doesNotMatch(source, /The record was not found, or this Admin API is not deployed/);
});

test("API Mode Admin dashboard marks unavailable summaries without sample totals", () => {
  const dashboard = section("  function dashboard(active)", "  function anyAdminDataError(resources)");

  assert.match(dashboard, /\["—", adminCatalogueSummary\.data \? adminCatalogueSummary\.data\.venues\.total/);
  assert.match(dashboard, /Account and booking summaries are not available yet/);
  assert.match(dashboard, /dataMode === "demo" \? '<p class="text-secondary small">Sample totals/);
  assert.match(dashboard, /Loading catalogue summary/);
  assert.match(dashboard, /summary\.time_slots\.total/);
  assert.match(dashboard, /var accountStats = dataMode === "demo" \? demoAccountStats\(\) : \[\]/);
  assert.match(dashboard, /var bookingStats = dataMode === "demo" \? demoBookingStats\(\) : \[\]/);
});

test("Admin catalogue summary is loaded from the Admin-only aggregate endpoint", () => {
  const loader = section("  function loadAdminCatalogueSummary(force)", "  function refreshSchedule()");

  assert.match(loader, /authUser\.role !== "ADMIN"/);
  assert.match(loader, /\/api\/v1\/admin\/catalogue\/summary/);
  assert.match(loader, /adminCatalogueSummary = \{ status: "loaded", data: summary/);
  assert.match(loader, /The catalogue summary response is invalid/);
});

test("Admin Users API Mode uses account APIs while Demo and unavailable Revenue remain separate", () => {
  const people = section("  function peoplePage()", "  function profilePage(");
  const revenue = section("  function revenuePage()", "  function peoplePage()");

  assert.match(source, /window\.AdminManagementApi\.listUsers/);
  assert.match(source, /window\.AdminManagementApi\.setUserActive/);
  assert.match(people, /You cannot change your own account status/);
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

test("Owner and Admin navigation share a read-only Settings page without a duplicate sidebar identity", () => {
  const settings = section("  function profilePage(active, admin)", "  function pageFor(active)");
  const shell = section("  function renderShell(content, admin, active)", "  function heading(active");

  assert.match(source, /\["owner-profile", "Settings", "bi-gear"\]/);
  assert.match(source, /\["admin-profile", "Settings", "bi-gear"\]/);
  assert.match(shell, /side-logout/);
  assert.doesNotMatch(shell, /class="side-user"/);
  assert.match(shell, /class="top-user"/);
  assert.match(settings, /Account Information/);
  assert.match(settings, /settings-account-details/);
  assert.match(settings, /Appearance/);
  assert.match(settings, /data-theme-choice="light"/);
  assert.match(settings, /data-theme-choice="dark"/);
  assert.doesNotMatch(settings, /profile-form|Change password|Edit profile/);
  assert.match(styles, /\.settings-layout \{ display: grid; width: min\(100%, 880px\)/);
  assert.match(styles, /\.settings-account-details dt[^}]*font-size: 14px/);
  assert.match(styles, /\.settings-account-details dd[^}]*font-size: 16px/);
  assert.match(source, /window\.ManagementTheme\.set\(button\.dataset\.themeChoice\)/);
  assert.match(source, /aria-pressed/);
  assert.match(source, /data-theme-status/);
  assert.match(styles, /\[data-theme="dark"\] \.modal-content/);
  assert.match(styles, /\[data-theme="dark"\] \.login-page/);
  assert.match(styles, /\[data-theme="dark"\] \.form-control/);
  assert.match(styles, /\[data-theme="dark"\] \.table thead th/);
  assert.match(styles, /--canvas: #17211b/);
  assert.match(styles, /--dark-surface: #202c24/);
  assert.match(styles, /--dark-raised: #29372e/);
  assert.match(styles, /\.main-column \{ min-width: 0;/);
});

test("API Mode is the default and Demo preview is selected only at sign-in", () => {
  assert.match(source, /var loginMode = "api"/);
  assert.match(source, /data-login-mode="demo"/);
  assert.match(source, /data-login-mode="api"/);
  assert.doesNotMatch(source, /court-mode-bar|modeToolbar\(\)|court-data-mode/);
  assert.match(source, /authUser\.role === "ADMIN" && \["sports", "venues", "courts", "slots"\]/);
  assert.match(source, /authUser\.role === "OWNER" && resource !== "sports"/);
});
