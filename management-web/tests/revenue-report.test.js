const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const appSource = fs.readFileSync(path.join(__dirname, "../assets/js/app.js"), "utf8");
const html = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "../assets/css/app.css"), "utf8");

test("revenue API sends filters through the authenticated shared API client", async () => {
  let requested;
  const window = { CourtApi: { get: (url) => { requested = url; return Promise.resolve({ ok: true }); } } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/revenue-api.js"), "utf8"), { window, URLSearchParams });
  await window.ManagementRevenueApi.getReport({
    date_from: "2026-03-01", date_to: "2026-03-31", timezone: "Asia/Ho_Chi_Minh", group_by: "month", page: 2, page_size: 20, sort: "asc"
  });
  assert.equal(requested, "/api/v1/payments/report?date_from=2026-03-01&date_to=2026-03-31&timezone=Asia%2FHo_Chi_Minh&group_by=month&page=2&page_size=20&sort=asc");
});

test("revenue API retrieves every matching page and stops if the report changes", async () => {
  const urls = [];
  const window = { CourtApi: { get: (url) => {
    urls.push(url);
    const query = new URLSearchParams(url.split("?")[1]);
    const page = Number(query.get("page"));
    const total = page === 3 ? 201 : 201;
    const count = page < 3 ? 100 : 1;
    return Promise.resolve({ transactions: { page, page_size: 100, total, items: Array.from({ length: count }, (_, i) => ({ payment_id: (page - 1) * 100 + i + 1 })) } });
  } } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/revenue-api.js"), "utf8"), { window, URLSearchParams });
  const rows = await window.ManagementRevenueApi.getAllTransactions({ date_from: "2026-03-01", date_to: "2026-03-31", timezone: "Asia/Ho_Chi_Minh", owner_id: "ignored" });
  assert.equal(rows.length, 201);
  assert.equal(urls.length, 3);
  assert.ok(urls.every((url) => url.includes("page_size=100") && url.includes("timezone=Asia%2FHo_Chi_Minh")));
  assert.ok(urls.every((url) => !url.includes("owner_id")));

  window.CourtApi.get = (url) => {
    const page = Number(new URLSearchParams(url.split("?")[1]).get("page"));
    return Promise.resolve({ transactions: { page, page_size: 100, total: page === 1 ? 101 : 102, items: Array.from({ length: 100 }, (_, i) => ({ payment_id: (page - 1) * 100 + i + 1 })) } });
  };
  await assert.rejects(window.ManagementRevenueApi.getAllTransactions({}), /changed while it was being exported/);
});

test("revenue presets use Vietnam calendar dates and handle week, month, five days, and one day", () => {
  const window = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/revenue-utils.js"), "utf8"), { window });
  const utils = window.ManagementRevenueUtils;
  const now = new Date("2026-11-15T05:00:00Z");
  assert.deepEqual(JSON.parse(JSON.stringify(utils.rangeForPreset("this-week", "", now))), {
    date_from: "2026-11-09", date_to: "2026-11-15", preset: "this-week", timezone: "Asia/Ho_Chi_Minh"
  });
  assert.deepEqual(JSON.parse(JSON.stringify(utils.rangeForPreset("this-month", "", now))), {
    date_from: "2026-11-01", date_to: "2026-11-30", preset: "this-month", timezone: "Asia/Ho_Chi_Minh"
  });
  assert.deepEqual(JSON.parse(JSON.stringify(utils.rangeForPreset("last-5-days", "", now))), {
    date_from: "2026-11-11", date_to: "2026-11-15", preset: "last-5-days", timezone: "Asia/Ho_Chi_Minh"
  });
  assert.deepEqual(JSON.parse(JSON.stringify(utils.rangeForPreset("specific-date", "2026-11-01", now))), {
    date_from: "2026-11-01", date_to: "2026-11-01", preset: "specific-date", timezone: "Asia/Ho_Chi_Minh"
  });
  assert.equal(utils.rangeForPreset("specific-date", "2026-02-30", now), null);
  assert.equal(utils.dateInTimeZone(new Date("2026-11-15T16:59:59Z")), "2026-11-15");
  assert.equal(utils.dateInTimeZone(new Date("2026-11-15T17:00:00Z")), "2026-11-16");
});

test("CSV export rejects duplicate payment rows across pages", async () => {
  let calls = 0;
  const window = { CourtApi: { get: () => {
    calls += 1;
    return Promise.resolve({ transactions: {
      page: calls, page_size: 1, total: 2,
      items: [{ payment_id: 7 }]
    } });
  } } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/revenue-api.js"), "utf8"), { window, URLSearchParams });
  await assert.rejects(window.ManagementRevenueApi.getAllTransactions({}), /report changed while it was being exported/);
});

test("CSV includes UTF-8 BOM, numeric amounts, provider method, and escaped fields without sensitive values", () => {
  const window = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/revenue-utils.js"), "utf8"), { window });
  const csv = window.ManagementRevenueUtils.buildCsv([{
    payment_id: 12, booking_id: 34, provider: 'BANK,"Transfer\nOnline', amount: "1200.50",
    status: "PAID", payment_date: "2026-03-10T17:00:00Z", transaction_code: "MUST_NOT_EXPORT", qr_token: "SECRET"
  }]);
  assert.ok(csv.startsWith("\uFEFFPayment ID,Booking ID,Payment Method,Amount,Payment Status,Payment Date (UTC)"));
  assert.match(csv, /12,34,"BANK,""Transfer\nOnline",1200\.50,PAID,2026-03-10T17:00:00Z/);
  assert.doesNotMatch(csv, /MUST_NOT_EXPORT|SECRET|User ID|idempotency/);
});

test("Owner and Admin Revenue pages share backend metrics and chart data without Demo fallback", () => {
  assert.match(appSource, /\["revenue", "Revenue"/);
  assert.match(appSource, /\["admin-revenue", "Revenue"/);
  assert.match(appSource, /ManagementRevenueApi\.getReport\(filters\)/);
  assert.match(appSource, /\["Total revenue", formatRevenueAmount/);
  assert.match(appSource, /summary\.pending_payments/);
  assert.match(appSource, /summary\.failed_payments/);
  assert.match(appSource, /summary\.total_transactions/);
  assert.match(appSource, /report\.revenue_series/);
  assert.match(appSource, /data-revenue-retry/);
  assert.match(appSource, /data-revenue-page/);
  assert.match(appSource, /<th>Method<\/th>/);
  assert.match(appSource, /item\.provider/);
  assert.doesNotMatch(appSource.slice(appSource.indexOf("function revenuePage(active)"), appSource.indexOf("function peoplePage()")), /<th>Transaction<\/th>|item\.transaction_code/);
  assert.match(appSource, /data-revenue-export/);
  assert.match(appSource, /var exportFilters = reportFiltersForApi\(1\)/);
  assert.match(appSource, /getAllTransactions\(exportFilters\)/);
  assert.match(appSource, /dashboardRevenueCard\(active\)/);
  assert.match(appSource, /active === "dashboard" && authUser && authUser\.role === "OWNER"\) \|\| \(active === "admin-dashboard" && authUser && authUser\.role === "ADMIN"/);
  assert.doesNotMatch(appSource, /legacy PAID payment\(s\)/);
  assert.doesNotMatch(appSource, /revenue-undated-note/);
  assert.doesNotMatch(appSource.slice(appSource.indexOf("function revenuePage(active)"), appSource.indexOf("function peoplePage()")), /Sample data|mock data|Download report/);
  assert.ok(html.indexOf("assets/js/revenue-utils.js") < html.indexOf("assets/js/app.js"));
  assert.ok(html.indexOf("assets/js/revenue-api.js") < html.indexOf("assets/js/app.js"));
});

test("Revenue method labels reflect the API provider and use Unknown when missing", () => {
  const start = appSource.indexOf("  function paymentMethodLabel(provider) {");
  const end = appSource.indexOf("  function exportRevenueCsv()", start);
  const label = vm.runInNewContext("(" + appSource.slice(start, end).trim() + ")");
  assert.equal(label("vnpay"), "VNPay");
  assert.equal(label("MOMO"), "MoMo");
  assert.equal(label("ZALOPAY"), "ZaloPay");
  assert.equal(label("MOCK"), "Mock");
  assert.equal(label("BANK_TRANSFER"), "Bank Transfer");
  assert.equal(label(undefined), "Unknown");
});

test("dashboard revenue is role-gated, uses independent loading/error states, and can retry", () => {
  const cardStart = appSource.indexOf("  function dashboardRevenueCard(active)");
  const cardEnd = appSource.indexOf("  function adminApiErrorMessage", cardStart);
  const card = appSource.slice(cardStart, cardEnd);
  const loaderStart = appSource.indexOf("  function loadRevenueReport(force)");
  const loaderEnd = appSource.indexOf("  function revenueChart(points)", loaderStart);
  const loader = appSource.slice(loaderStart, loaderEnd);
  assert.match(card, /dataMode !== "api"/);
  assert.match(card, /authUser\.role !== "OWNER" && authUser\.role !== "ADMIN"/);
  assert.match(card, /state\.status === "idle" \|\| state\.status === "loading"/);
  assert.match(card, /state\.status === "error"/);
  assert.match(card, /data-revenue-retry/);
  assert.doesNotMatch(card, /dashboard-revenue-chart|revenueChart\(/);
  assert.match(loader, /ManagementRevenueApi\.getReport\(filters\)/);
  assert.match(loader, /revenueState\.promise && revenueState\.filtersKey === filtersKey/);
  assert.match(appSource, /active === "dashboard" && authUser && authUser\.role === "OWNER"/);
  assert.match(appSource, /active === "admin-dashboard" && authUser && authUser\.role === "ADMIN"/);
  assert.match(appSource, /if \(active === "admin-dashboard" && dataMode === "api"\) loadAdminDashboardSummaries\(false\)/);
  const ownerRevenue = appSource.slice(appSource.indexOf("function revenuePage(active)"), appSource.indexOf("function peoplePage()"));
  assert.match(ownerRevenue, /owner \? "" : '<div class="panel-card revenue-chart-card"/);
  assert.match(ownerRevenue, /owner \? "" : '<label><span>Chart grouping/);
});

test("Revenue chart and tables remain scrollable and responsive at narrow widths", () => {
  assert.match(css, /\.revenue-chart-scroll \{ overflow-x: auto; \}/);
  assert.match(css, /\.revenue-table \{ min-width: 880px; \}/);
  assert.match(css, /@media \(max-width: 560px\)[\s\S]*\.revenue-filter-toolbar/);
  assert.match(css, /\.revenue-stat-grid \{ display: grid;/);
});
