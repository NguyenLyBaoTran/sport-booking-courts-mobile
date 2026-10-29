const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const appSource = fs.readFileSync(path.join(__dirname, "../assets/js/app.js"), "utf8");
const htmlSource = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");

function loadUtils() {
  const window = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../assets/js/schedule-utils.js"), "utf8"), { window, globalThis: {} });
  return window.ScheduleUtils;
}

test("normalizes Vietnamese and ISO dates without local timezone conversion", () => {
  const utils = loadUtils();
  assert.deepEqual({ ...utils.parseDateInput("23/10/2026") }, { valid: true, iso: "2026-10-23" });
  assert.deepEqual({ ...utils.parseDateInput("2026-10-23") }, { valid: true, iso: "2026-10-23" });
  assert.equal(utils.parseDateInput("31/02/2026").valid, false);
  assert.equal(utils.parseDateInput("23/13/2026").valid, false);
});

test("matches full and day/month schedule searches against the slot calendar date", () => {
  const utils = loadUtils();
  assert.equal(utils.matchesDateSearch("23/10/2026", "2026-10-23"), true);
  assert.equal(utils.matchesDateSearch("2026-10-23", "2026-10-23"), true);
  assert.equal(utils.matchesDateSearch("23/10", "2026-10-23"), true);
  assert.equal(utils.matchesDateSearch("23/10", "2025-10-23"), true);
  assert.equal(utils.matchesDateSearch("23/10/2026", "2026-10-24"), false);
  assert.equal(utils.matchesDateSearch("31/02/2026", "2026-02-31"), false);
  assert.equal(utils.matchesDateSearch("Demo Sports Center", "2026-10-23"), null);
});

test("filters court choices to the selected venue", () => {
  const utils = loadUtils();
  const courts = [
    { id: 1, venue_id: 10 },
    { id: 2, venue_id: 20 },
    { id: 3, venue_id: 10 }
  ];
  assert.deepEqual(Array.from(utils.courtsForVenue(courts, "10"), (court) => court.id), [1, 3]);
  assert.deepEqual(Array.from(utils.courtsForVenue(courts, "missing")), []);
});

test("Date Filter compares normalized calendar dates and allows clearing", () => {
  const utils = loadUtils();
  assert.equal(utils.matchesDateFilter("2026-10-23", "2026-10-23"), true);
  assert.equal(utils.matchesDateFilter("23/10/2026", "2026-10-23"), true);
  assert.equal(utils.matchesDateFilter("2026-10-24", "2026-10-23"), false);
  assert.equal(utils.matchesDateFilter("", "2026-10-23"), true);
});

test("calendar selection normalizes the Date Filter and preserves other filters", () => {
  const utils = loadUtils();
  const filters = { search: "Court", date: "", venueId: "2", courtId: "8", status: "true" };
  assert.deepEqual({ ...utils.selectScheduleDate(filters, "2026-10-23") }, { ...filters, date: "2026-10-23" });
  assert.equal(utils.selectScheduleDate(filters, "2026-02-31"), null);
  assert.equal(filters.date, "");
  assert.equal(utils.formatDateDisplay("2026-10-23"), "23/10/2026");
});

test("shared calendar grid supports direct month/year selection without page render", () => {
  const utils = loadUtils();
  const october = utils.calendarDays(2026, 9);
  assert.equal(october.length, 42);
  assert.equal(october[3].iso, "2026-10-01"); // Thursday, Monday-first calendar
  assert.equal(october[3].inMonth, true);
  assert.ok(october.some((day) => day.iso === "2026-09-30" && !day.inMonth));
  const monthYearHandlers = appSource.slice(appSource.indexOf('var monthSelect = picker.querySelector("[data-calendar-month]");'), appSource.indexOf('var previousMonth = picker.querySelector("[data-calendar-previous]");'));
  assert.match(monthYearHandlers, /data-calendar-year/);
  assert.match(monthYearHandlers, /updateCalendarGrid\(picker\)/);
  assert.doesNotMatch(monthYearHandlers, /render\(\)/);
  assert.match(appSource, /for \(var year = 1900; year <= 2100; year \+= 1\)/);
  const updateStart = appSource.indexOf("  function updateCalendarGrid(picker) {");
  const updateEnd = appSource.indexOf("  function setCalendarDate", updateStart);
  const updateCode = appSource.slice(updateStart, updateEnd);
  assert.match(updateCode, /button\.textContent = day\.day/);
  assert.doesNotMatch(updateCode, /innerHTML|render\(\)/);
});

test("calendar day selection updates Schedule date and reset clears all Schedule filters", () => {
  const selectionStart = appSource.indexOf('picker.addEventListener("click", function (event) {');
  const selectionEnd = appSource.indexOf('function retryButton()', selectionStart);
  const selection = appSource.slice(selectionStart, selectionEnd);
  assert.match(selection, /selectScheduleDate\(scheduleFilters, selectedDate\)/);
  assert.match(selection, /render\(\)/);
  const resetStart = appSource.indexOf('var scheduleReset = document.querySelector("[data-schedule-reset]");');
  const resetEnd = appSource.indexOf('var slotVenue', resetStart);
  const reset = appSource.slice(resetStart, resetEnd);
  assert.match(reset, /scheduleFilters = scheduleUtils\.emptyFilters\(\)/);
  assert.match(reset, /render\(\)/);
});

test("all date controls share one read-only calendar picker with direct month/year controls", () => {
  assert.equal((appSource.match(/data-schedule-date/g) || []).length, 2); // one markup attribute and one state lookup
  assert.match(appSource, /class="form-control calendar-date-trigger/);
  assert.match(appSource, /calendarPickerMarkup\("schedule-filter"/);
  assert.match(appSource, /calendarPickerMarkup\("booking-filter"/);
  assert.match(appSource, /calendarPickerMarkup\("slot-date"/);
  assert.match(appSource, /fieldName: "slot_date", required: true/);
  assert.match(appSource, /data-calendar-month/);
  assert.match(appSource, /data-calendar-year/);
  assert.doesNotMatch(appSource, /type="date"/);
  assert.match(appSource, /event\.key === "Escape"\) document\.querySelectorAll\('\[data-calendar-picker\]/);
  assert.match(appSource, /calendarOpenIds\[picker\.dataset\.calendarId\]/);
  assert.match(appSource, /document\.querySelectorAll\("\[data-calendar-picker\]"\)\.forEach/);
});

test("calendar assets and the updated app use cache versions", () => {
  assert.match(htmlSource, /assets\/css\/app\.css\?v=20261025-shared-calendar-1/);
  assert.match(htmlSource, /assets\/js\/schedule-utils\.js\?v=20261025-shared-calendar-1/);
  assert.match(htmlSource, /assets\/js\/app\.js\?v=20261029-owner-checkin-1/);
});

test("Schedule Date, Venue, Court, Status and date Search filters combine", () => {
  const utils = loadUtils();
  const slot = { slot_date: "2026-10-23", start_time: "08:00:00", end_time: "09:00:00", court_id: 8, is_active: true };
  const related = { venueId: 2, venueName: "Central Venue", courtName: "Court 8", sportName: "Tennis" };
  const filters = { search: "23/10/2026", date: "2026-10-23", venueId: "2", courtId: "8", status: "true" };
  assert.equal(utils.matchesScheduleFilters(slot, related, filters), true);
  assert.equal(utils.matchesScheduleFilters(slot, related, { ...filters, date: "2026-10-24" }), false);
  assert.equal(utils.matchesScheduleFilters(slot, related, { ...filters, venueId: "3" }), false);
  assert.equal(utils.matchesScheduleFilters(slot, related, { ...filters, courtId: "9" }), false);
  assert.equal(utils.matchesScheduleFilters(slot, related, { ...filters, status: "false" }), false);
  assert.equal(utils.matchesScheduleFilters(slot, related, { ...filters, search: "2026-10-23" }), true);
  assert.equal(utils.matchesScheduleFilters(slot, related, { ...filters, search: "23/10" }), true);
});

test("future-start validation uses frozen Vietnam business time and permits unchanged history", () => {
  const utils = loadUtils();
  const now = new Date("2026-10-25T03:00:00.000Z"); // 10:00 in Asia/Ho_Chi_Minh
  assert.equal(utils.businessDateTime(now), "2026-10-25T10:00:00");
  assert.equal(utils.validateFutureStart({ slot_date: "2026-10-24", start_time: "08:00:00" }, null, now), "Start time must be in the future (Vietnam time).");
  assert.equal(utils.validateFutureStart({ slot_date: "2026-10-25", start_time: "09:30:00" }, null, now), "Start time must be in the future (Vietnam time).");
  assert.equal(utils.validateFutureStart({ slot_date: "2026-10-25", start_time: "10:00:00" }, null, now), "Start time must be in the future (Vietnam time).");
  assert.equal(utils.validateFutureStart({ slot_date: "2026-10-25", start_time: "10:30:00" }, null, now), "");
  const old = { slot_date: "2026-10-24", start_time: "08:00:00" };
  assert.equal(utils.validateFutureStart({ slot_date: "2026-10-24", start_time: "08:00:00", end_time: "09:30:00" }, old, now), "");
  assert.equal(utils.validateFutureStart({ slot_date: "2026-10-24", start_time: "08:30:00" }, old, now), "Start time must be in the future (Vietnam time).");
});

test("Demo Schedule refresh cancel preserves data; confirm resets only slots", () => {
  const utils = loadUtils();
  const slots = [{ id: 90, court_id: 1 }];
  const venues = [{ id: 1, name: "custom venue" }];
  const bookings = [{ id: "B-1" }];
  const demoData = { slots, venues, bookings };
  const starterSlots = [{ id: 1, court_id: 1 }];
  assert.equal(utils.refreshDemoSchedule(demoData, false, starterSlots), false);
  assert.equal(demoData.slots, slots);
  assert.equal(demoData.venues, venues);
  assert.equal(demoData.bookings, bookings);
  assert.equal(utils.refreshDemoSchedule(demoData, true, starterSlots), true);
  assert.equal(demoData.slots, starterSlots);
  assert.equal(demoData.venues, venues);
  assert.equal(demoData.bookings, bookings);
});

test("API Schedule refresh fetches only Time Slot collections and handles empty courts", async () => {
  const utils = loadUtils();
  const requests = [];
  const slots = await utils.fetchTimeSlotsForCourts([{ id: 2 }, { id: 5 }], async (path) => {
    requests.push(path);
    return [{ court_id: Number(path.split("=")[1]) }];
  });
  assert.deepEqual(requests, ["/api/v1/time-slots?court_id=2", "/api/v1/time-slots?court_id=5"]);
  assert.deepEqual(Array.from(slots, (slot) => slot.court_id), [2, 5]);
  assert.deepEqual(Array.from(await utils.fetchTimeSlotsForCourts([], async (path) => { requests.push(path); return []; })), []);
  assert.equal(requests.length, 2);
});

test("time slot overlap is limited to the same court and date", () => {
  const utils = loadUtils();
  const existing = [{ id: 1, court_id: 10, slot_date: "2026-10-23", start_time: "08:00:00", end_time: "09:00:00", is_active: true }];
  const overlap = { court_id: 10, slot_date: "2026-10-23", start_time: "08:30:00", end_time: "09:30:00", is_active: true };
  const otherCourt = { ...overlap, court_id: 11 };
  const otherDate = { ...overlap, slot_date: "2026-10-24" };
  assert.equal(utils.hasTimeSlotOverlap(existing, overlap, null), true);
  assert.equal(utils.hasTimeSlotOverlap(existing, otherCourt, null), false);
  assert.equal(utils.hasTimeSlotOverlap(existing, otherDate, null), false);
  assert.equal(utils.hasTimeSlotOverlap(existing, { ...overlap, start_time: "09:00:00", end_time: "10:00:00" }, 1), false);
});

test("Reset Filters creates defaults without mutating supplied state", () => {
  const utils = loadUtils();
  const filters = { search: "Court", date: "2026-10-23", courtId: "1", venueId: "2", status: "true" };
  const data = { slots: [{ id: 1 }] };
  assert.deepEqual({ ...utils.emptyFilters() }, { search: "", date: "", courtId: "", venueId: "", status: "" });
  assert.equal(filters.search, "Court");
  assert.equal(filters.date, "2026-10-23");
  assert.equal(data.slots.length, 1);
});

test("Schedule renders one calendar filter and keeps reset controls consolidated", () => {
  assert.equal((appSource.match(/data-schedule-date/g) || []).length, 2); // one picker instance is rendered for Schedule
  assert.doesNotMatch(appSource, /type="date"[^\n]*data-schedule-date/);
  assert.doesNotMatch(appSource, /data-schedule-date-clear|data-schedule-demo-reset/);
  assert.match(appSource, /data-schedule-reset>Reset filters/);
  assert.match(appSource, /data-schedule-retry/);
  assert.match(appSource, /crudOpenButton\("slots", null, "Add time slot"/);
  assert.match(appSource, /calendarPickerMarkup\("slot-date", "Date", record && record\.slot_date/);
});

test("Owner Bookings date filter uses calendar selection and reset clears its value", () => {
  assert.match(appSource, /calendarPickerMarkup\("booking-filter", "Filter booking date", bookingDate/);
  assert.match(appSource, /bookingDate = bookingDateInput \? bookingDateInput\.dataset\.dateValue/);
  assert.match(appSource, /setCalendarDate\(bookingDatePicker, ""\)/);
  assert.match(appSource, /booking\.date === bookingDate/);
});

test("Schedule refresh confirms Demo reset and uses GET collection loading in API Mode", () => {
  const start = appSource.indexOf("  function refreshSchedule() {");
  const end = appSource.indexOf("  function renderKeepingFocus(", start);
  const refreshCode = appSource.slice(start, end);
  assert.match(refreshCode, /Reset the demo schedule to its original data\? Your demo schedule changes will be lost\./);
  assert.match(refreshCode, /refreshDemoSchedule\(demoCourtData, true/);
  assert.match(refreshCode, /fetchTimeSlotsForCourts\(courts, fetchCollection\)/);
  assert.doesNotMatch(refreshCode, /CourtApi\.(post|put|delete)\(/);
});
