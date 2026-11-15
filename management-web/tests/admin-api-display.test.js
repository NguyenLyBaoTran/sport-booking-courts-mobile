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
  const checkins = section("  function checkinPage(active, admin)", "  function setScanResult(");

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
  const checkins = section("  function checkinPage(active, admin)", "  function setScanResult(");

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

test("API Mode Admin dashboard renders all three backend summary groups without Demo values", () => {
  const dashboard = section("  function dashboard(active)", "  function anyAdminDataError(resources)");
  assert.match(dashboard, /dashboardSummaryGroup\("catalogue"/);
  assert.match(dashboard, /dashboardSummaryGroup\("users"/);
  assert.match(dashboard, /dashboardSummaryGroup\("bookings"/);
  for (const field of ["sports.total", "venues.total", "courts.total", "time_slots.active", "users.total", "users.active", "users.inactive", "owners.total", "bookings.total", "bookings.checked_in", "bookings.completed"]) {
    assert.ok(dashboard.includes("summary." + field), "missing summary field " + field);
  }
  const apiBranch = dashboard.slice(dashboard.indexOf('      if (dataMode === "api")'), dashboard.indexOf('      var activeSlots'));
  assert.doesNotMatch(apiBranch, /demoAccountStats|demoBookingStats|Sample totals|adminCatalogueSummary/);
});

test("Admin summary loading is ADMIN-only, validates contracts and isolates group failures", () => {
  const loader = section("  function isSummaryCount(value)", "  function adminApiErrorMessage(error, context)");
  assert.match(loader, /authUser\.role !== "ADMIN"/);
  assert.match(loader, /validateDashboardSummary\(kind, summary\)/);
  assert.match(loader, /adminDashboardSummaryPromises\[kind\]/);
  assert.match(loader, /Promise\.all\(\["catalogue", "users", "bookings"\]/);
  assert.match(loader, /retryAdminDashboardSummary\(kind\)/);
  assert.match(loader, /data-admin-summary-retry=/);
  assert.match(loader, /Loading .* summary/);
  assert.match(loader, /status === 401/);
  assert.match(loader, /status === 403/);
  assert.match(loader, /status >= 500/);
  assert.match(source, /if \(active === "admin-dashboard" && dataMode === "api"\) loadAdminDashboardSummaries\(false\)/);
  assert.match(source, /role === "OWNER" && requestedAdmin/);
  assert.match(source, /No user or owner accounts are available yet/);
  assert.match(source, /No bookings are available yet/);
});
test("Admin Users API Mode uses account APIs and revenue uses the reporting API", () => {
  const people = section("  function peoplePage()", "  function profilePage(");
  const revenue = section("  function revenuePage(active)", "  function peoplePage()");

  assert.match(source, /window\.AdminManagementApi\.listUsers/);
  assert.match(source, /window\.AdminManagementApi\.setUserActive/);
  assert.match(people, /You cannot change your own account status/);
  assert.match(people, /var rows = data\.people/);
  assert.match(source, /window\.ManagementRevenueApi\.getReport/);
  assert.match(revenue, /revenuePresetButtons\(revenueFilters\.preset\)/);
  assert.match(revenue, /data-revenue-specific-date/);
  assert.match(revenue, /data-revenue-export/);
  assert.match(revenue, /revenueChart\(report\.revenue_series\)/);
  assert.match(revenue, /No transactions are available for this period/);
  assert.doesNotMatch(revenue, /Sample data|mock data|var values = \[42, 61/);
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

test("Production login uses API authentication without a Demo session path", () => {
  const login = section("  function renderLogin()", "  function renderShell(");
  assert.match(source, /var dataMode = "api"/);
  assert.doesNotMatch(source, /demoRole|managementDemoRole/);
  assert.doesNotMatch(source, /BookingMockData|CourtDemoData|BookingDemoData/);
  assert.doesNotMatch(login, /Demo preview|data-login-mode|Optional in Demo Mode/);
  assert.doesNotMatch(source, /court-mode-bar|modeToolbar\(\)|court-data-mode/);
  assert.match(source, /\["admin-revenue", "Revenue"/);
  assert.match(source, /role === "OWNER" && requestedAdmin/);
  assert.match(source, /authUser\.role === "ADMIN" && \["sports", "venues", "courts", "slots"\]/);
  assert.match(source, /authUser\.role === "OWNER" && resource !== "sports"/);
});
