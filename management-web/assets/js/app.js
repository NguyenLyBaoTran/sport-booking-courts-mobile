(function () {
  "use strict";
  var data = window.BookingMockData;
  var authUtils = window.ManagementAuthUtils;
  var scheduleUtils = window.ScheduleUtils;
  var dataMode = readDemoRole() ? "demo" : "api";
  var demoCourtData = window.CourtDemoData.create();
  var demoBookings = window.BookingDemoData.create();
  var bookingSearch = "";
  var bookingDate = "";
  var bookingStatus = "";
  var bookingVenueId = "";
  var ownerBookingVenueIds = [];
  var ownerBookingsState = { status: "idle", data: [], error: "" };
  var ownerBookingsRequestId = 0;
  var ownerBookingCompletionPending = false;
  var venueSearch = "";
  var courtSearch = "";
  var sportSearch = "";
  var registryTab = "venues";
  var registryFilters = { sportId: "", active: "", venueId: "" };
  var qrScanner = null;
  var scannerInstance = null;
  var scannerStarting = false;
  var scannerStartPromise = null;
  var scannerStopPromise = null;
  var scannerEpoch = 0;
  var scannerState = "idle";
  var scannerScanGate = window.QrScanGate.create();
  var ownerCheckinPending = false;
  var scanResult = null;
  var crudFormState = null;
  var courtResources = {
    sports: { status: "idle", data: [], error: "" },
    venues: { status: "idle", data: [], error: "" },
    courts: { status: "idle", data: [], error: "" },
    slots: { status: "idle", data: [], error: "" }
  };
  var scheduleState = { status: "idle", data: [], error: "" };
  var scheduleRefreshPromise = null;
  var courtLoadPromise = null;
  var adminCatalogueSummary = { status: "idle", data: null, error: "" };
  var adminCatalogueSummaryPromise = null;
  var adminUsersState = { status: "idle", data: null, error: "", requestId: 0 };
  var adminBookingsState = { status: "idle", data: null, error: "", requestId: 0 };
  var adminCheckinsState = { status: "idle", data: null, error: "", requestId: 0 };
  var adminUsersFilters = { page: 1, page_size: 25, q: "", role: "", is_active: "" };
  var adminBookingsFilters = { page: 1, page_size: 25, booking_id: "", status: "", date_from: "", date_to: "", venue_id: "", court_id: "", owner_id: "", user_id: "" };
  var adminCheckinsFilters = { page: 1, page_size: 25, booking_id: "", date_from: "", date_to: "", venue_id: "", court_id: "", checked_in_by: "" };
  var authUser = null;
  var demoRole = readDemoRole();
  var authRestorePromise = null;
  var authMessage = "";
  var loginMode = "demo";
  var loginWorkspace = "OWNER";
  var loginEmailValue = "";
  var scheduleFilters = { search: "", date: "", courtId: "", venueId: "", status: "" };
  var calendarViews = {};
  var calendarOpenIds = {};
  var ownerNav = [
    ["dashboard", "Dashboard", "bi-grid-1x2"],
    ["venues", "Venue & Court", "bi-buildings"],
    ["schedule", "Schedule", "bi-calendar3"],
    ["owner-bookings", "Bookings", "bi-journal-check"],
    ["qr-checkin", "QR Check-in", "bi-qr-code-scan"],
    ["revenue", "Revenue", "bi-graph-up-arrow"],
    ["owner-profile", "Profile", "bi-person-circle"]
  ];
  var adminNav = [
    ["admin-dashboard", "Dashboard", "bi-grid-1x2"],
    ["people", "Users & Owners", "bi-people"],
    ["admin-venues", "Venues & Courts", "bi-buildings"],
    ["admin-schedule", "Time Slots", "bi-calendar3"],
    ["admin-bookings", "Bookings", "bi-journal-check"],
    ["checkins", "Check-ins", "bi-qr-code"],
    ["admin-profile", "Profile", "bi-person-circle"]
  ];
  var info = {
    dashboard: ["Owner dashboard", "Welcome back", "Your venues, courts, and daily operations."],
    venues: ["Venue management", "Venue & Court", "Manage your sports venues, courts, and availability."],
    schedule: ["Court operations", "Facility Schedule", "Review your court availability for this week."],
    "owner-bookings": ["Owner operations", "Bookings Management", "Manage court reservations across your venues."],
    "qr-checkin": ["Front desk", "QR Check-in", "Verify a booking before play begins."],
    revenue: ["Business overview", "Revenue & Payouts", "Review revenue information for your venues."],
    "owner-profile": ["Account settings", "Owner Profile", "Your account information."],
    "admin-dashboard": ["System overview", "Admin Dashboard", "Review the shared sports and venue catalogue."],
    people: ["Directory", "Users & Court Owners", "Account directory."],
    "admin-venues": ["Platform registry", "Venue & Court", "Review the sports, venue, and court catalogue."],
    "admin-schedule": ["Platform operations", "Time Slot Management", "Manage time slots across all venues."],
    "admin-bookings": ["Platform activity", "Global Bookings", "Review booking activity."],
    checkins: ["Platform activity", "Check-in Management", "Review recent booking check-ins."],
    "admin-profile": ["Account settings", "Admin Profile", "Your account information."]
  };
  var statSets = {
    dashboard: [["bi-calendar-check", "Today’s bookings"], ["bi-people", "Active customers"], ["bi-building", "My venues"], ["bi-currency-exchange", "Revenue this month"]],
    "admin-dashboard": [["bi-people", "Users"], ["bi-buildings", "Venues"], ["bi-grid-3x3", "Courts"], ["bi-journal-check", "Bookings"]],
    "admin-dashboard-demo": [["bi-people", "Users"], ["bi-buildings", "Owners"], ["bi-journal-check", "Bookings"], ["bi-currency-exchange", "Booking value"]],
    venues: [["bi-buildings", "My venues"], ["bi-grid-3x3", "Total courts"], ["bi-clock-history", "Available slots"], ["bi-check-circle", "Open venues"]],
    bookings: [["bi-journal-check", "Bookings today"], ["bi-currency-exchange", "Revenue today"], ["bi-check2-circle", "Checked in"], ["bi-hourglass-split", "Needs attention"]],
    revenue: [["bi-currency-exchange", "Revenue this month"], ["bi-graph-up-arrow", "Revenue this week"], ["bi-wallet2", "Pending payout"], ["bi-calendar2-check", "Paid out this month"]],
    people: [["bi-people", "Demo accounts"], ["bi-person-check", "User accounts"], ["bi-building-check", "Owner accounts"], ["bi-person-exclamation", "Pending accounts"]],
    "admin-venues": [["bi-buildings", "Total venues"], ["bi-grid-3x3", "Courts listed"], ["bi-check-circle", "Open venues"], ["bi-hourglass-split", "Needs review"]],
    checkins: [["bi-qr-code", "Check-ins today"], ["bi-shield-check", "Verified"], ["bi-building", "Active venues"], ["bi-exclamation-circle", "Manual reviews"]],
    "admin-bookings": [["bi-journal-check", "Sample bookings"], ["bi-currency-exchange", "Sample booking value"], ["bi-check2-circle", "Checked in"], ["bi-hourglass-split", "Pending"]],
    "court-overview": [["bi-trophy", "Sports"], ["bi-buildings", "Venues"], ["bi-grid-3x3", "Courts"], ["bi-clock-history", "Active slot records"]],
    "court-registry": [["bi-trophy", "Sports"], ["bi-buildings", "Venues"], ["bi-grid-3x3", "Courts"], ["bi-check-circle", "Active venues"]]
  };

  function currentRoute() {
    return (location.hash.replace(/^#\/?/, "") || "login").toLowerCase();
  }
  function readDemoRole() {
    try {
      var role = window.sessionStorage.getItem("managementDemoRole");
      return role === "OWNER" || role === "ADMIN" ? role : "";
    } catch (error) { return ""; }
  }
  function currentRole() {
    return (authUser && authUser.role) || demoRole || "";
  }
  function homeRouteForRole(role) {
    return authUtils.homeRouteForRole(role);
  }
  function clearSession() {
    window.CourtApi.clearAccessToken();
    try { window.sessionStorage.removeItem("managementDemoRole"); } catch (error) { /* storage may be unavailable */ }
    authUser = null;
    demoRole = "";
    authRestorePromise = null;
    courtResources = {
      sports: { status: "idle", data: [], error: "" },
      venues: { status: "idle", data: [], error: "" },
      courts: { status: "idle", data: [], error: "" },
      slots: { status: "idle", data: [], error: "" }
    };
    scheduleState = { status: "idle", data: [], error: "" };
    courtLoadPromise = null;
    scheduleRefreshPromise = null;
  }
  function currentResources(allowDemo) {
    if (!allowDemo || dataMode !== "demo") return courtResources;
    return {
      sports: { status: "loaded", data: demoCourtData.sports, error: "" },
      venues: { status: "loaded", data: demoCourtData.venues, error: "" },
      courts: { status: "loaded", data: demoCourtData.courts, error: "" },
      slots: { status: "loaded", data: demoCourtData.slots, error: "" }
    };
  }
  function modeToolbar() {
    var demo = dataMode === "demo";
    var adminRegistry = currentRoute() === "admin-dashboard" || currentRoute() === "admin-venues" || currentRoute() === "admin-schedule";
    var message = demo
      ? (adminRegistry && currentRoute() !== "admin-schedule" ? "Sample catalogue for preview. Changes reset when you reload." : "Preview changes are saved only in this browser.")
      : (adminRegistry ? "Manage the shared sports and court catalogue." : (authUser && authUser.role === "OWNER" ? "Manage your venues, courts, schedule, and reservations." : "Review system information."));
    return '<section class="court-mode-bar" aria-label="Data source"><div><strong>' +
      (demo ? "Demo data" : "Live data") + '</strong><small>' + message +
      '</small></div><label class="small mb-0" for="court-data-mode">Data source</label><select id="court-data-mode" class="form-select" aria-label="Select data source"><option value="api" ' +
      (!demo ? "selected" : "") + '>Live data</option><option value="demo" ' +
      (demo ? "selected" : "") + '>Demo data</option></select></section>';
  }
  function recordsFor(resource) {
    return demoCourtData[resource];
  }
  function nextDemoId(records) {
    return records.reduce(function (max, item) { return Math.max(max, Number(item.id) || 0); }, 0) + 1;
  }
  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }
  function fetchCollection(path) {
    return window.CourtApi.get(path).then(function (items) {
      if (!Array.isArray(items)) throw new Error("The API returned an unexpected list response.");
      return items;
    });
  }
  function loadCourtResources(force) {
    if (courtLoadPromise) return force ? courtLoadPromise.then(function () { return loadCourtResources(true); }) : courtLoadPromise;
    if (!force && Object.keys(courtResources).every(function (key) { return courtResources[key].status !== "idle"; })) return Promise.resolve();
    var keys = ["sports", "venues", "courts", "slots"];
    keys.forEach(function (key) { courtResources[key] = { status: "loading", data: force ? courtResources[key].data : [], error: "" }; });
    function fetchResource(key, path) {
      return fetchCollection(path).then(function (items) {
        courtResources[key] = { status: "loaded", data: items, error: "" };
        return items;
      }).catch(function (error) {
        courtResources[key] = { status: "error", data: [], error: error.message || "Could not load data." };
        return null;
      });
    }
    function loadOwnedResources() {
      var ownerId = encodeURIComponent(authUser.id);
      return Promise.all([fetchResource("sports", "/api/v1/sports"), fetchResource("venues", "/api/v1/venues?owner_id=" + ownerId)]).then(function (results) {
        var venues = results[1];
        if (venues === null) {
          courtResources.courts = { status: "error", data: [], error: "Could not load the current Owner's venues." };
          courtResources.slots = { status: "error", data: [], error: "Time Slots are unavailable because the Owner's Courts could not be loaded." };
          return;
        }
        if (!venues.length) {
          courtResources.courts = { status: "loaded", data: [], error: "" };
          courtResources.slots = { status: "loaded", data: [], error: "" };
          return;
        }
        return Promise.all(venues.map(function (venue) { return fetchCollection("/api/v1/courts?venue_id=" + encodeURIComponent(venue.id)); })).then(function (courtGroups) {
          var courts = [].concat.apply([], courtGroups);
          courtResources.courts = { status: "loaded", data: courts, error: "" };
          if (!courts.length) {
            courtResources.slots = { status: "loaded", data: [], error: "" };
            return;
          }
          return Promise.all(courts.map(function (court) { return fetchCollection("/api/v1/time-slots?court_id=" + encodeURIComponent(court.id)); })).then(function (slotGroups) {
            courtResources.slots = { status: "loaded", data: [].concat.apply([], slotGroups), error: "" };
          });
        }).catch(function (error) {
          courtResources.courts = { status: "error", data: [], error: error.message || "Could not load Courts." };
          courtResources.slots = { status: "error", data: [], error: "Time Slots are unavailable because Courts could not be loaded." };
        });
      });
    }
    function loadAllResources() {
      var requests = { sports: "/api/v1/sports", venues: "/api/v1/venues", courts: "/api/v1/courts", slots: "/api/v1/time-slots" };
      return Promise.all(Object.keys(requests).map(function (key) { return fetchResource(key, requests[key]); }));
    }
    render();
    courtLoadPromise = (authUser && authUser.role === "OWNER" ? loadOwnedResources() : loadAllResources()).then(function () {
      scheduleState = {
        status: courtResources.slots.status,
        data: courtResources.slots.data,
        error: courtResources.slots.error
      };
    }).finally(function () {
      courtLoadPromise = null;
      render();
    });
    return courtLoadPromise;
  }
  function loadAdminCatalogueSummary(force) {
    if (dataMode !== "api" || !authUser || authUser.role !== "ADMIN") return Promise.resolve();
    if (adminCatalogueSummaryPromise) return adminCatalogueSummaryPromise;
    if (!force && adminCatalogueSummary.status !== "idle") return Promise.resolve();
    adminCatalogueSummary = { status: "loading", data: adminCatalogueSummary.data, error: "" };
    adminCatalogueSummaryPromise = window.CourtApi.get("/api/v1/admin/catalogue/summary").then(function (summary) {
      ["sports", "venues", "courts", "time_slots"].forEach(function (key) {
        if (!summary || !summary[key] || typeof summary[key].total !== "number" || typeof summary[key].active !== "number") {
          throw new Error("The catalogue summary response is invalid.");
        }
      });
      adminCatalogueSummary = { status: "loaded", data: summary, error: "" };
    }).catch(function (error) {
      adminCatalogueSummary = { status: "error", data: null, error: error.message || "Could not load catalogue summary." };
    }).finally(function () {
      adminCatalogueSummaryPromise = null;
      if (currentRoute() === "admin-dashboard" && dataMode === "api") render();
    });
    return adminCatalogueSummaryPromise;
  }
  function adminApiErrorMessage(error) {
    var status = error && error.status;
    if (status === 401) return "Your session expired or you are not signed in. Sign in again.";
    if (status === 403) return "This account does not have Admin permission.";
    if (status === 404) return "The record was not found, or this Admin API is not deployed in the connected service yet.";
    if (status === 409) return "The account status change conflicts with current Admin safeguards.";
    if (status === 422) return "The filters or request are invalid.";
    if (status === 503 || status === 504 || status === 0) return "The management service is temporarily unavailable. Try again.";
    return "Could not load Admin data. Try again.";
  }
  function loadAdminPage(kind, filters) {
    if (dataMode !== "api" || !authUser || authUser.role !== "ADMIN" || !window.AdminManagementApi) return Promise.resolve();
    var states = { users: adminUsersState, bookings: adminBookingsState, checkins: adminCheckinsState };
    var state = states[kind];
    var requestId = state.requestId + 1;
    state.requestId = requestId;
    state.status = "loading";
    state.error = "";
    if (currentRoute() === (kind === "users" ? "people" : kind === "bookings" ? "admin-bookings" : "checkins")) render();
    var load = kind === "users" ? window.AdminManagementApi.listUsers(filters)
      : (kind === "bookings" ? window.AdminManagementApi.listBookings(filters) : window.AdminManagementApi.listCheckins(filters));
    return load.then(function (result) {
      if (state.requestId !== requestId) return;
      state.status = "loaded";
      state.data = result;
    }).catch(function (error) {
      if (state.requestId !== requestId) return;
      state.status = "error";
      state.error = adminApiErrorMessage(error);
    }).finally(function () {
      if (state.requestId === requestId && currentRoute() === (kind === "users" ? "people" : kind === "bookings" ? "admin-bookings" : "checkins")) render();
    });
  }
  function adminPagination(kind, result) {
    if (!result) return "";
    var pages = Math.max(1, Math.ceil(result.total / result.page_size));
    return '<div class="d-flex justify-content-between align-items-center gap-2 flex-wrap mt-3"><small class="text-secondary">Page ' + result.page + ' of ' + pages + ' · ' + result.total + ' records</small><div class="d-flex gap-2"><button class="btn btn-sm btn-outline-secondary" type="button" data-admin-page="' + kind + '" data-page="' + Math.max(1, result.page - 1) + '" ' + (result.page <= 1 ? "disabled" : "") + '>Previous</button><button class="btn btn-sm btn-outline-secondary" type="button" data-admin-page="' + kind + '" data-page="' + Math.min(pages, result.page + 1) + '" ' + (result.page >= pages ? "disabled" : "") + '>Next</button></div></div>';
  }
  function adminListState(state) {
    if (state.status === "idle" || state.status === "loading") return '<div class="panel-body text-secondary" role="status">Loading records...</div>';
    if (state.status === "error") return '<div class="panel-body"><div class="alert alert-warning mb-0" role="alert">' + esc(state.error) + ' <button class="btn btn-sm btn-outline-secondary ms-2" type="button" data-admin-retry>Retry</button></div></div>';
    if (!state.data || !state.data.items.length) return '<div class="panel-body text-secondary" role="status">No records match these filters.</div>';
    return "";
  }
  function refreshSchedule() {
    if (dataMode === "demo") {
      showActionConfirmation("Reset Demo Schedule", "Reset the demo schedule to its original data? Your demo schedule changes will be lost.", "Reset Schedule", function () {
        scheduleUtils.refreshDemoSchedule(demoCourtData, true, window.CourtDemoData.create().slots);
        scheduleFilters = scheduleUtils.emptyFilters();
        calendarViews["schedule-filter"] = null;
        calendarOpenIds["schedule-filter"] = false;
        if (crudFormState && crudFormState.resource === "slots") crudFormState = null;
        render();
        toast("Demo schedule restored. Filters were cleared so all sample slots are visible.");
      });
      return;
    }
    if (scheduleRefreshPromise) return scheduleRefreshPromise;
    var currentSlots = scheduleState.data;
    if (courtResources.courts.status === "error") {
      toast("Could not refresh time slots: " + (courtResources.courts.error || "Court list is unavailable."));
      return;
    }
    var courts = courtResources.courts.data.slice();
    scheduleState = { status: "loading", data: currentSlots, error: "" };
    render();
    scheduleRefreshPromise = scheduleUtils.fetchTimeSlotsForCourts(courts, fetchCollection).then(function (slots) {
      courtResources.slots = { status: "loaded", data: slots, error: "" };
      scheduleState = { status: "loaded", data: slots, error: "" };
      toast("Time slots refreshed.");
    }).catch(function (error) {
      var message = error.message || "Could not load time slots.";
      scheduleState = { status: "error", data: currentSlots, error: message };
      courtResources.slots = { status: "error", data: currentSlots, error: message };
      toast("Could not refresh time slots: " + message);
    }).finally(function () {
      scheduleRefreshPromise = null;
      render();
    });
    return scheduleRefreshPromise;
  }
  function renderKeepingFocus(element) {
    var key = element && element.dataset ? element.dataset.focusKey : "";
    var supportsSelection = element && (element.type === "search" || element.type === "text");
    var start = supportsSelection && typeof element.selectionStart === "number" ? element.selectionStart : null;
    var end = supportsSelection && typeof element.selectionEnd === "number" ? element.selectionEnd : null;
    render();
    if (!key) return;
    var replacement = document.querySelector('[data-focus-key="' + key + '"]');
    if (!replacement) return;
    replacement.focus();
    if (start !== null && (replacement.type === "search" || replacement.type === "text") && typeof replacement.setSelectionRange === "function") replacement.setSelectionRange(start, end);
  }
  function getCalendarView(pickerId, selectedDate) {
    if (!calendarViews[pickerId]) {
      var initialDate = selectedDate || scheduleUtils.businessDateTime().slice(0, 10);
      var parsed = scheduleUtils.parseDateInput(initialDate);
      var parts = (parsed.valid ? parsed.iso : scheduleUtils.businessDateTime().slice(0, 10)).split("-");
      calendarViews[pickerId] = { year: Number(parts[0]), month: Number(parts[1]) - 1 };
    }
    return calendarViews[pickerId];
  }
  function calendarGridMarkup(view, selectedDate) {
    return scheduleUtils.calendarDays(view.year, view.month).map(function (day) {
      var classes = "calendar-day" + (day.inMonth ? "" : " is-outside") + (day.iso === selectedDate ? " is-selected" : "");
      return '<button type="button" class="' + classes + '" data-calendar-day="' + day.iso + '" aria-pressed="' + (day.iso === selectedDate) + '" aria-label="' + day.iso + '">' + day.day + '</button>';
    }).join("");
  }
  function calendarPickerMarkup(pickerId, label, value, options) {
    options = options || {};
    var parsed = scheduleUtils.parseDateInput(value);
    var selectedDate = parsed.valid ? parsed.iso : "";
    var view = getCalendarView(pickerId, selectedDate);
    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    var monthOptions = months.map(function (month, index) { return '<option value="' + index + '" ' + (index === view.month ? "selected" : "") + '>' + month + '</option>'; }).join("");
    var yearOptions = "";
    for (var year = 1900; year <= 2100; year += 1) yearOptions += '<option value="' + year + '" ' + (year === view.year ? "selected" : "") + '>' + year + '</option>';
    var displayDate = scheduleUtils.formatDateDisplay(selectedDate) || "Choose date";
    var required = options.required ? ' <span class="required-mark" aria-label="required">*</span>' : "";
    var fieldLabel = options.label ? '<label class="form-label" for="calendar-trigger-' + esc(pickerId) + '">' + esc(label) + required + '</label>' : "";
    var hiddenValue = options.fieldName ? '<input type="hidden" name="' + esc(options.fieldName) + '" value="' + esc(selectedDate) + '" data-calendar-field>' : "";
    var filterAttribute = options.filterAttribute || (pickerId === "schedule-filter" ? " data-schedule-date" : (pickerId === "booking-filter" ? " data-booking-date" : ""));
    return '<div class="calendar-picker" data-calendar-picker data-calendar-id="' + esc(pickerId) + '" data-date-value="' + esc(selectedDate) + '">' + fieldLabel + hiddenValue +
      '<button type="button" class="form-control calendar-date-trigger' + (options.required ? ' calendar-date-required' : '') + '" id="calendar-trigger-' + esc(pickerId) + '" data-calendar-toggle data-date-value="' + esc(selectedDate) + '"' + filterAttribute + ' aria-haspopup="dialog" aria-expanded="false" aria-label="' + esc(label) + '"><span class="calendar-date-label">' + esc(displayDate) + '</span><i class="bi bi-calendar3" aria-hidden="true"></i></button>' +
      '<div class="calendar-popover" data-calendar-popover role="dialog" aria-label="Choose ' + esc(label.toLowerCase()) + '" hidden><div class="calendar-navigation"><button type="button" class="btn btn-sm btn-outline-secondary" data-calendar-previous aria-label="Previous month"><i class="bi bi-chevron-left"></i></button><select class="form-select" data-calendar-month aria-label="Calendar month">' + monthOptions + '</select><select class="form-select" data-calendar-year aria-label="Calendar year">' + yearOptions + '</select><button type="button" class="btn btn-sm btn-outline-secondary" data-calendar-next aria-label="Next month"><i class="bi bi-chevron-right"></i></button></div><div class="calendar-weekdays" aria-hidden="true"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div><div class="calendar-days" data-calendar-days>' + calendarGridMarkup(view, selectedDate) + '</div></div></div>';
  }
  function updateCalendarGrid(picker) {
    if (!picker) return;
    var pickerId = picker.dataset.calendarId;
    var selectedDate = picker.dataset.dateValue || "";
    var view = getCalendarView(pickerId, selectedDate);
    var dayButtons = picker.querySelectorAll("[data-calendar-day]");
    var dayValues = scheduleUtils.calendarDays(view.year, view.month);
    dayButtons.forEach(function (button, index) {
      var day = dayValues[index];
      if (!day) return;
      var selected = day.iso === selectedDate;
      button.dataset.calendarDay = day.iso;
      button.textContent = day.day;
      button.className = "calendar-day" + (day.inMonth ? "" : " is-outside") + (selected ? " is-selected" : "");
      button.setAttribute("aria-pressed", String(selected));
      button.setAttribute("aria-label", day.iso);
    });
    var month = picker.querySelector("[data-calendar-month]");
    var year = picker.querySelector("[data-calendar-year]");
    if (month) month.value = String(view.month);
    if (year) year.value = String(view.year);
  }
  function setCalendarDate(picker, value) {
    var parsed = scheduleUtils.parseDateInput(value);
    if (!picker || (value && !parsed.valid)) return false;
    var selectedDate = parsed.valid ? parsed.iso : "";
    var pickerId = picker.dataset.calendarId;
    picker.dataset.dateValue = selectedDate;
    var label = picker.querySelector(".calendar-date-label");
    var hidden = picker.querySelector("[data-calendar-field]");
    var toggle = picker.querySelector("[data-calendar-toggle]");
    if (toggle) toggle.dataset.dateValue = selectedDate;
    if (label) label.textContent = scheduleUtils.formatDateDisplay(selectedDate) || "Choose date";
    if (hidden) hidden.value = selectedDate;
    var parts = selectedDate.split("-");
    if (parts.length === 3) calendarViews[pickerId] = { year: Number(parts[0]), month: Number(parts[1]) - 1 };
    updateCalendarGrid(picker);
    return true;
  }
  function shiftCalendarMonth(picker, delta) {
    var view = getCalendarView(picker.dataset.calendarId, picker.dataset.dateValue);
    var shifted = new Date(Date.UTC(view.year, view.month + delta, 1));
    calendarViews[picker.dataset.calendarId] = { year: shifted.getUTCFullYear(), month: shifted.getUTCMonth() };
    updateCalendarGrid(picker);
  }
  function closeCalendarPicker(picker, restoreFocus) {
    if (!picker) picker = document.querySelector('[data-calendar-picker][data-calendar-open="true"]');
    if (!picker) return;
    var calendar = picker.querySelector("[data-calendar-popover]");
    var toggle = picker.querySelector("[data-calendar-toggle]");
    if (!calendar) return;
    if (calendar.hidden) {
      picker.dataset.calendarOpen = "false";
      calendarOpenIds[picker.dataset.calendarId] = false;
      return;
    }
    calendar.hidden = true;
    picker.dataset.calendarOpen = "false";
    calendarOpenIds[picker.dataset.calendarId] = false;
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      if (restoreFocus) toggle.focus();
    }
  }
  function wireCalendarPicker(picker) {
    var toggle = picker.querySelector("[data-calendar-toggle]");
    var calendar = picker.querySelector("[data-calendar-popover]");
    var pickerId = picker.dataset.calendarId;
    if (!toggle || !calendar) return;
    toggle.addEventListener("click", function () {
      if (!calendar.hidden) { closeCalendarPicker(picker, false); return; }
      getCalendarView(pickerId, picker.dataset.dateValue);
      updateCalendarGrid(picker);
      calendar.hidden = false;
      picker.dataset.calendarOpen = "true";
      calendarOpenIds[pickerId] = true;
      toggle.setAttribute("aria-expanded", "true");
    });
    var monthSelect = picker.querySelector("[data-calendar-month]");
    var yearSelect = picker.querySelector("[data-calendar-year]");
    if (monthSelect) monthSelect.addEventListener("change", function () {
      calendarViews[pickerId].month = Number(monthSelect.value);
      updateCalendarGrid(picker);
    });
    if (yearSelect) yearSelect.addEventListener("change", function () {
      calendarViews[pickerId].year = Number(yearSelect.value);
      updateCalendarGrid(picker);
    });
    var previousMonth = picker.querySelector("[data-calendar-previous]");
    var nextMonth = picker.querySelector("[data-calendar-next]");
    if (previousMonth) previousMonth.addEventListener("click", function () { shiftCalendarMonth(picker, -1); });
    if (nextMonth) nextMonth.addEventListener("click", function () { shiftCalendarMonth(picker, 1); });
    picker.addEventListener("click", function (event) {
      var dayButton = event.target.closest("[data-calendar-day]");
      if (!dayButton) return;
      var selectedDate = dayButton.dataset.calendarDay;
      if (!scheduleUtils.parseDateInput(selectedDate).valid) return;
      if (pickerId === "schedule-filter") {
        var selectedFilters = scheduleUtils.selectScheduleDate(scheduleFilters, selectedDate);
        if (!selectedFilters) return;
        scheduleFilters = selectedFilters;
        setCalendarDate(picker, selectedDate);
        calendarOpenIds[pickerId] = false;
        render();
      } else if (pickerId === "booking-filter") {
        bookingDate = selectedDate;
        setCalendarDate(picker, selectedDate);
        closeCalendarPicker(picker, false);
        if (dataMode === "demo") applyBookingFilters();
        else loadOwnerBookings();
      } else if (pickerId.indexOf("admin-bookings-") === 0 || pickerId.indexOf("admin-checkins-") === 0) {
        var adminKind = pickerId.indexOf("admin-bookings-") === 0 ? "bookings" : "checkins";
        var adminFilters = adminKind === "bookings" ? adminBookingsFilters : adminCheckinsFilters;
        adminFilters[pickerId.slice(pickerId.lastIndexOf("-") + 1) === "from" ? "date_from" : "date_to"] = selectedDate;
        adminFilters.page = 1;
        setCalendarDate(picker, selectedDate);
        closeCalendarPicker(picker, false);
        loadAdminPage(adminKind, adminFilters);
      } else {
        setCalendarDate(picker, selectedDate);
        var error = picker.closest("form") && picker.closest("form").querySelector('[data-field-error="slot_date"]');
        if (error) error.textContent = "";
        var trigger = picker.querySelector("[data-calendar-toggle]");
        if (trigger) { trigger.classList.remove("is-invalid"); trigger.removeAttribute("aria-invalid"); }
        closeCalendarPicker(picker, false);
      }
    });
  }
  function retryButton() {
    return '<button class="btn btn-sm btn-outline-secondary" data-court-retry>Retry</button>';
  }
  function pendingWriteNotice() {
    if (dataMode === "demo") {
      return '<div class="alert alert-info py-2 small" role="status"><strong>Demo Mode:</strong> Changes affect only the in-memory sample data. Reload the page to restore the starter data.</div>';
    }
    if (authUser && authUser.role === "OWNER") return '<div class="alert alert-info py-2 small" role="status">You can manage your venues, courts, and time slots. Sports are managed centrally.</div>';
    if (authUser && authUser.role === "ADMIN") return '<div class="alert alert-info py-2 small" role="status">Manage the shared sports, venue, court, and time slot catalogue.</div>';
    return '<div class="alert alert-warning py-2 small" role="status">This catalogue is currently read-only.</div>';
  }
  function demoNotice(message) {
    return '<div class="alert alert-info py-2 small" role="status"><strong>Demo:</strong> ' + esc(message) + '</div>';
  }
  function courtStatus(active) {
    return badge(active ? "Active" : "Inactive");
  }
  function apiTime(value) {
    return esc(String(value || "").slice(0, 5));
  }
  function apiDate(value) {
    var parts = String(value || "").split("-");
    return parts.length === 3 ? esc(parts[2] + "/" + parts[1] + "/" + parts[0]) : esc(value || "");
  }
  function formatPriceVnd(value) {
    var parts = String(value === null || value === undefined ? "" : value).split(".");
    var whole = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    var fraction = (parts[1] || "").replace(/0+$/, "");
    return esc(whole + (fraction ? "," + fraction : "") + " VND/hour");
  }
  function resourceError(label, error) {
    var gatewayOffline = /failed to fetch|networkerror|connection refused|load failed/i.test(String(error || ""));
    return '<div class="alert alert-danger d-flex justify-content-between align-items-center gap-2" role="alert"><span>' + (gatewayOffline ? "Could not load the latest information. Check your connection and try again." : "Could not load " + esc(label) + ". " + esc(error || "Please try again.")) + '</span>' + retryButton() + "</div>";
  }
  function crudOpenButton(resource, id, label, style) {
    return '<button type="button" class="btn btn-sm ' + (style || "btn-outline-secondary") + '" data-crud-open="' + esc(resource) + '" data-crud-id="' + esc(id === undefined ? "" : id) + '">' + esc(label) + "</button>";
  }
  function crudDeleteButton(resource, id) {
    var enabled = dataMode === "demo" || (authUser && ((authUser.role === "ADMIN" && ["sports", "venues", "courts", "slots"].indexOf(resource) >= 0) || (authUser.role === "OWNER" && resource !== "sports")));
    return '<button type="button" class="btn btn-sm btn-outline-danger" data-crud-delete="' + esc(resource) + '" data-crud-id="' + esc(id) + '" ' + (!enabled ? 'disabled title="This action is not available for this account"' : "") + '>Delete</button>';
  }
  function formInput(label, name, value, type, attributes, full) {
    var required = /\brequired\b/.test(attributes || "");
    return '<div class="' + (full ? "crud-field-full" : "") + '"><label class="form-label" for="crud-' + name + '">' + label + (required ? ' <span class="required-mark" aria-label="required">*</span>' : "") +
      '</label><input class="form-control" id="crud-' + name + '" name="' + name + '" type="' + (type || "text") + '" value="' + esc(value === null || value === undefined ? "" : value) + '" ' + (attributes || "") + (required ? ' aria-required="true"' : "") + '><div class="field-error" data-field-error="' + name + '" aria-live="polite"></div></div>';
  }
  function formTextarea(label, name, value, attributes) {
    return '<div class="crud-field-full"><label class="form-label" for="crud-' + name + '">' + label +
      '</label><textarea class="form-control" id="crud-' + name + '" name="' + name + '" ' + (attributes || "") + '>' + esc(value || "") + "</textarea><div class=\"field-error\" data-field-error=\"" + name + "\" aria-live=\"polite\"></div></div>";
  }
  function formSelect(label, name, items, selected, textFor) {
    var options = items.map(function (item) {
      return '<option value="' + esc(item.id) + '" ' + (String(item.id) === String(selected) ? "selected" : "") + '>' + esc(textFor(item)) + "</option>";
    }).join("");
    return '<div><label class="form-label" for="crud-' + name + '">' + label + ' <span class="required-mark" aria-label="required">*</span></label><select class="form-select" id="crud-' + name + '" name="' + name + '" required aria-required="true"><option value="">Choose ' + label.toLowerCase() + "</option>" + options + "</select><div class=\"field-error\" data-field-error=\"" + name + "\" aria-live=\"polite\"></div></div>";
  }
  function timeSelect(label, name, value) {
    var selected = value ? apiTime(value) : "";
    var options = '<option value="">Choose ' + label.toLowerCase() + '</option>';
    for (var minutes = 0; minutes < 24 * 60; minutes += 30) {
      var hour = String(Math.floor(minutes / 60)).padStart(2, "0");
      var minute = String(minutes % 60).padStart(2, "0");
      var timeValue = hour + ":" + minute;
      options += '<option value="' + timeValue + '" ' + (selected === timeValue ? "selected" : "") + '>' + timeValue + '</option>';
    }
    return '<div><label class="form-label" for="crud-' + name + '">' + label + ' <span class="required-mark" aria-label="required">*</span></label><select class="form-select" id="crud-' + name + '" name="' + name + '" required aria-required="true">' + options + '</select><div class="field-error" data-field-error="' + name + '" aria-live="polite"></div></div>';
  }
  function formActiveField(active) {
    return '<label class="crud-field-full form-check"><input class="form-check-input" type="checkbox" name="is_active" ' + (active ? "checked" : "") + '><span class="form-check-label">Active</span></label>';
  }
  function crudFormMarkup(resource, resources) {
    if (!crudFormState || crudFormState.resource !== resource) return "";
    var records = dataMode === "demo" ? recordsFor(resource) : resources[resource].data;
    var record = crudFormState.id === null ? null : records.find(function (item) { return String(item.id) === String(crudFormState.id); });
    var editing = !!record;
    var title = (editing ? "Edit " : "Add ") + ({ sports: "Sport", venues: "Venue", courts: "Court", slots: "Time Slot" }[resource]);
    var fields = "";
    if (resource === "sports") {
      fields = formInput("Name", "name", record && record.name, "text", 'maxlength="100" required') +
        formTextarea("Description", "description", record && record.description, "") + formActiveField(!record || record.is_active);
    } else if (resource === "venues") {
      if (dataMode === "api" && authUser && authUser.role === "ADMIN") fields += formInput("Owner user ID", "owner_id", record && record.owner_id, "number", 'min="1" step="1" required');
      else if (dataMode === "api") fields += '<div class="crud-field-full small text-secondary">Owner ID: ' + esc(authUser ? authUser.id : "Unavailable") + ' (taken from your authenticated account)</div>';
      else fields += '<div class="crud-field-full small text-secondary">Owner: Demo preview, not linked to an account</div>';
      fields += formInput("Name", "name", record && record.name, "text", 'maxlength="200" required') +
        formInput("Address", "address", record && record.address, "text", 'maxlength="255" required', true) +
        formTextarea("Description", "description", record && record.description, "") +
        formInput("Phone", "phone", record && record.phone, "tel", 'maxlength="20"') + formActiveField(!record || record.is_active);
    } else if (resource === "courts") {
      fields = formSelect("Venue", "venue_id", resources.venues.data, record && record.venue_id, function (item) { return item.name; }) +
        formSelect("Sport", "sport_id", resources.sports.data, record && record.sport_id, function (item) { return item.name; }) +
        formInput("Name", "name", record && record.name, "text", 'maxlength="100" required') +
        formInput("Price per hour (VND)", "price_per_hour", record && record.price_per_hour, "text", 'inputmode="decimal" placeholder="120000.00" required') +
        formTextarea("Description", "description", record && record.description, "") + formActiveField(!record || record.is_active);
    } else {
      var slotCourt = record && resources.courts.data.find(function (item) { return String(item.id) === String(record.court_id); });
      var selectedVenueId = slotCourt ? slotCourt.venue_id : "";
      var filteredCourts = selectedVenueId ? scheduleUtils.courtsForVenue(resources.courts.data, selectedVenueId) : [];
      var courtPlaceholder = selectedVenueId ? (filteredCourts.length ? "Choose court" : "No courts for this venue") : "Choose a venue first";
      var courtOptions = filteredCourts.map(function (item) {
        return '<option value="' + esc(item.id) + '" ' + (record && String(item.id) === String(record.court_id) ? "selected" : "") + '>' + esc(item.name) + '</option>';
      }).join("");
      fields = formSelect("Venue", "venue_id", resources.venues.data, selectedVenueId, function (item) { return item.name; }) +
        '<div><label class="form-label" for="crud-court_id">Court <span class="required-mark" aria-label="required">*</span></label><select class="form-select" id="crud-court_id" name="court_id" data-slot-court required aria-required="true"><option value="">' + courtPlaceholder + '</option>' + courtOptions + '</select><div class="field-error" data-field-error="court_id" aria-live="polite"></div></div>' +
        calendarPickerMarkup("slot-date", "Date", record && record.slot_date, { fieldName: "slot_date", required: true, label: true }) +
        timeSelect("Start time", "start_time", record && record.start_time) +
        timeSelect("End time", "end_time", record && record.end_time) + formActiveField(!record || record.is_active);
    }
    var prerequisiteNotice = "";
    if (dataMode === "api" && resource === "courts" && resources.sports.status === "loaded" && !resources.sports.data.length) {
      prerequisiteNotice = '<div class="crud-field-full alert alert-warning py-2 small" role="status">No Sports are available. An ADMIN must create a Sport before Court creation.</div>';
    }
    if (dataMode === "api" && resource === "slots" && resources.courts.status === "loaded" && !resources.courts.data.length) {
      prerequisiteNotice = '<div class="crud-field-full alert alert-warning py-2 small" role="status">No Courts are available. Create a Venue and Court with an existing Sport before adding Time Slots.</div>';
    }
    var apiWritable = dataMode === "api" && authUser && ((authUser.role === "ADMIN" && ["sports", "venues", "courts", "slots"].indexOf(resource) >= 0) || (authUser.role === "OWNER" && resource !== "sports"));
    var canSave = dataMode === "demo" || apiWritable;
    var save = dataMode === "demo"
      ? '<button type="submit" class="btn btn-success">Save in Demo Mode</button>'
      : '<button type="submit" class="btn btn-success" ' + (canSave ? "" : "disabled") + '>' + (canSave ? "Save changes" : "View only") + '</button>';
    return '<form class="crud-form-card" data-crud-form data-crud-resource="' + resource + '" data-crud-id="' + (record ? esc(record.id) : "") + '" novalidate><div class="d-flex justify-content-between align-items-center"><h3>' + title +
      '</h3><span class="badge-soft ' + (dataMode === "demo" || apiWritable ? "" : "warning") + '">' + (dataMode === "demo" ? "Demo only" : (apiWritable ? (authUser.role === "ADMIN" ? "Admin access" : "Owner access") : "View only")) + '</span></div><div class="crud-grid">' + prerequisiteNotice + fields +
      '</div><div class="crud-form-footer">' +
      '<button type="button" class="btn btn-outline-secondary" data-crud-cancel>Cancel</button>' + save + '</div></form>';
  }
  function validateDemoForm(resource, values, id) {
    if (resource === "sports") {
      if (!values.name || values.name.length > 100) return { field: "name", message: "Enter a sport name with at most 100 characters." };
      if (demoCourtData.sports.some(function (item) { return String(item.id) !== String(id) && item.name.toLowerCase() === values.name.toLowerCase(); })) return { field: "name", message: "A sport with this name already exists." };
    }
    if (resource === "venues") {
      if (!values.name || values.name.length > 200) return { field: "name", message: "Enter a venue name with at most 200 characters." };
      if (!values.address || values.address.length > 255) return { field: "address", message: "Enter a venue address with at most 255 characters." };
      if (values.phone && values.phone.length > 20) return { field: "phone", message: "Phone must be at most 20 characters." };
    }
    if (resource === "courts") {
      if (!values.name || values.name.length > 100) return { field: "name", message: "Enter a court name with at most 100 characters." };
      if (!demoCourtData.venues.some(function (item) { return String(item.id) === String(values.venue_id); })) return { field: "venue_id", message: "Choose a valid venue." };
      if (!demoCourtData.sports.some(function (item) { return String(item.id) === String(values.sport_id); })) return { field: "sport_id", message: "Choose a valid sport." };
      if (!/^\d{1,10}(?:\.\d{1,2})?$/.test(values.price_per_hour) || /^0+(?:\.0{1,2})?$/.test(values.price_per_hour)) return { field: "price_per_hour", message: "Price must be greater than zero with at most 2 decimal places." };
    }
    if (resource === "slots") {
      if (!demoCourtData.courts.some(function (item) { return String(item.id) === String(values.court_id); })) return { field: "court_id", message: "Choose a valid court." };
      var chosenCourt = demoCourtData.courts.find(function (item) { return String(item.id) === String(values.court_id); });
      if (!chosenCourt || String(chosenCourt.venue_id) !== String(values.venue_id)) return { field: "court_id", message: "Choose a court that belongs to the selected venue." };
      if (!scheduleUtils.parseDateInput(values.slot_date).valid) return { field: "slot_date", message: "Enter a valid date as dd/MM/yyyy, for example 23/10/2026." };
      if (!values.start_time || !values.end_time || values.start_time.slice(0, 5) >= values.end_time.slice(0, 5)) return { field: "end_time", message: "Ensure start time is earlier than end time." };
      var halfHourTime = /^(?:[01]\d|2[0-3]):(?:00|30)$/;
      if (!halfHourTime.test(values.start_time.slice(0, 5)) || !halfHourTime.test(values.end_time.slice(0, 5))) return { field: "start_time", message: "Choose start and end times in 30-minute increments." };
      var existingSlot = id ? demoCourtData.slots.find(function (item) { return String(item.id) === String(id); }) : null;
      var futureError = scheduleUtils.validateFutureStart(values, existingSlot);
      if (futureError) return { field: "start_time", message: futureError };
      if (scheduleUtils.hasTimeSlotOverlap(demoCourtData.slots, values, id)) return { field: "start_time", message: "This time range duplicates or overlaps another slot for the selected court." };
    }
    return null;
  }
  function demoFormValues(form, resource) {
    var values = Object.fromEntries(new FormData(form).entries());
    values.is_active = form.elements.is_active.checked;
    ["name", "address", "description", "phone", "price_per_hour"].forEach(function (key) {
      if (values[key] === undefined || values[key] === null) values[key] = "";
    });
    ["name", "address", "description", "phone", "price_per_hour"].forEach(function (key) {
      if (values[key] !== undefined) values[key] = values[key].trim();
    });
    if (resource === "courts") {
      values.venue_id = Number(values.venue_id);
      values.sport_id = Number(values.sport_id);
      values.price_per_hour = values.price_per_hour;
      if (!values.description) values.description = null;
    }
    if (resource === "venues") {
      if (!values.description) values.description = null;
      if (!values.phone) values.phone = null;
      values.owner_id = null;
      values.created_at = null;
    }
    if (resource === "sports" && !values.description) values.description = null;
    if (resource === "slots") {
      values.venue_id = Number(values.venue_id);
      values.court_id = Number(values.court_id);
      var date = scheduleUtils.parseDateInput(values.slot_date);
      if (date.valid) values.slot_date = date.iso;
      values.start_time += ":00";
      values.end_time += ":00";
    }
    return values;
  }
  function resourceForApi(resource) {
    return resource === "slots" ? "time-slots" : resource;
  }
  function detailButton(resource, id, label) {
    return '<button class="btn btn-sm btn-outline-secondary" data-resource-detail="' + esc(resource) + '" data-resource-id="' + esc(id) + '">' + esc(label || "Details") + "</button>";
  }
  function showResourceDetails(resource, item) {
    var fields = {
      sports: [["id", "ID"], ["name", "Name"], ["description", "Description"], ["is_active", "Status"]],
      venues: [["id", "ID"], ["owner_id", "Owner ID"], ["name", "Name"], ["address", "Address"], ["description", "Description"], ["phone", "Phone"], ["is_active", "Status"], ["created_at", "Created"]],
      courts: [["id", "ID"], ["venue_id", "Venue ID"], ["sport_id", "Sport ID"], ["name", "Court"], ["description", "Description"], ["price_per_hour", "Price/hour"], ["is_active", "Status"]],
      "time-slots": [["id", "ID"], ["court_id", "Court ID"], ["slot_date", "Date"], ["start_time", "Start"], ["end_time", "End"], ["is_active", "Status"]]
    }[resource] || [];
    var title = { sports: "Sport details", venues: "Venue details", courts: "Court details", "time-slots": "Time slot details" }[resource] || "Details";
    var rows = fields.filter(function (field) {
      return item[field[0]] !== null && item[field[0]] !== undefined && item[field[0]] !== "";
    }).map(function (field) {
      var value = item[field[0]];
      if (field[0] === "is_active") value = value ? "Active" : "Inactive";
      if (field[0] === "price_per_hour") value = formatPriceVnd(value);
      else if (field[0] === "start_time" || field[0] === "end_time") value = apiTime(value);
      else value = esc(value === null || value === undefined || value === "" ? "—" : value);
      return '<div class="detail-row"><span>' + field[1] + '</span><strong>' + value + "</strong></div>";
    }).join("");
    var host = document.getElementById("api-detail-modal-host");
    if (!host) {
      host = document.createElement("div");
      host.id = "api-detail-modal-host";
      document.body.appendChild(host);
    }
    host.innerHTML = '<div class="modal fade" id="api-detail-modal" tabindex="-1" aria-labelledby="api-detail-title" aria-hidden="true"><div class="modal-dialog modal-dialog-centered modal-dialog-scrollable resource-detail-modal"><div class="modal-content"><div class="modal-header"><h2 class="modal-title fs-6" id="api-detail-title">' + title + '</h2><button type="button" class="btn-close" data-modal-close aria-label="Close"></button></div><div class="modal-body"><div class="resource-details-grid">' + rows + '</div></div><div class="modal-footer"><button type="button" class="btn btn-outline-secondary" data-modal-close>Close</button></div></div></div></div>';
    var modal = document.getElementById("api-detail-modal");
    showManagedModal(modal, host);
  }
  function routeLink(id) { return "#/" + id; }
  function navMarkup(items, active) {
    return items.map(function (item) {
      return '<a class="side-link ' + (active === item[0] ? "active" : "") + '" href="' + routeLink(item[0]) + '"><i class="bi ' + item[2] + '"></i><span>' + item[1] + "</span></a>";
    }).join("");
  }
  function renderLogin() {
    document.title = "Sign in | Sports Court Booking";
    var isApiMode = !authUtils.workspaceVisible(loginMode);
    document.getElementById("app").innerHTML =
      '<main class="login-page"><section class="login-art">' +
      '<div class="login-brand brand p-0"><span class="brand-mark"><i class="bi bi-trophy"></i></span><span>Courtbook<small>Sports Court Booking</small></span></div>' +
      '<div class="login-message"><p class="eyebrow">Management workspace</p><h1>Run your courts.<br>Keep the game moving.</h1><p>Manage venues, schedules, reservations, and check-ins.</p></div>' +
      '<div class="login-art-foot">Sports Court Booking ? Management</div></section>' +
      '<section class="login-form-side"><form class="login-card" id="login-form" novalidate><p class="eyebrow">Welcome back</p><h2>Sign in to your account</h2><p>Access your management workspace.</p>' +
      '<div class="login-mode-switch" role="group" aria-label="Sign-in option"><button type="button" class="' + (!isApiMode ? "active" : "") + '" data-login-mode="demo" aria-pressed="' + (!isApiMode) + '">Demo preview</button><button type="button" class="' + (isApiMode ? "active" : "") + '" data-login-mode="api" aria-pressed="' + isApiMode + '">Sign in</button></div>' +
      (!isApiMode ? '<div class="login-mode-note" role="status">Preview with sample data. No account is needed.</div><label class="form-label" for="login-workspace">Workspace</label><select class="form-select" id="login-workspace"><option value="OWNER" ' + (loginWorkspace === "OWNER" ? "selected" : "") + '>Court Owner</option><option value="ADMIN" ' + (loginWorkspace === "ADMIN" ? "selected" : "") + '>Admin</option></select>' : '<div class="login-mode-note" role="status">Sign in with your account. Your role opens the matching workspace.</div>') +
      '<label class="form-label" for="login-email">Email address</label><input class="form-control" id="login-email" type="email" autocomplete="username" value="' + esc(loginEmailValue) + '" placeholder="name@example.com" ' + (isApiMode ? "required" : "") + '>' +
      '<label class="form-label" for="login-password">Password</label><input class="form-control" id="login-password" type="password" autocomplete="current-password" ' + (isApiMode ? "required" : "") + ' placeholder="' + (isApiMode ? "Enter your password" : "Optional in Demo Mode") + '">' +
      '<button class="btn btn-success w-100" type="submit" data-login-submit>' + (isApiMode ? 'Sign in' : 'Open workspace') + ' <i class="bi bi-arrow-right ms-1"></i></button>' +
      (authMessage ? '<div class="alert alert-danger mt-3" role="alert">' + esc(authMessage) + '</div>' : '') +
      '<div class="login-footnote">' + (isApiMode ? 'Your sign-in stays in the live workspace.' : 'Sample data stays separate from your account.') + '</div></form></section></main>';

    document.querySelectorAll("[data-login-mode]").forEach(function (button) {
      button.addEventListener("click", function () {
        loginEmailValue = document.getElementById("login-email").value.trim();
        loginMode = authUtils.normalizeMode(button.dataset.loginMode);
        authMessage = "";
        renderLogin();
      });
    });
    var emailInput = document.getElementById("login-email");
    emailInput.addEventListener("input", function () { loginEmailValue = emailInput.value; });
    var workspaceInput = document.getElementById("login-workspace");
    if (workspaceInput) workspaceInput.addEventListener("change", function () { loginWorkspace = workspaceInput.value; });
    document.getElementById("login-form").addEventListener("submit", function (event) {
      event.preventDefault();
      var email = emailInput.value.trim();
      var password = document.getElementById("login-password").value;
      var plan = authUtils.loginPlan(loginMode, loginWorkspace, email, password);
      if (!plan.valid) {
        authMessage = plan.message;
        renderLogin();
        return;
      }
      authMessage = "";
      if (plan.mode === "demo") {
        clearSession();
        demoRole = plan.role;
        try { window.sessionStorage.setItem("managementDemoRole", demoRole); } catch (error) { /* storage may be unavailable */ }
        dataMode = "demo";
        loginEmailValue = "";
        location.hash = "#" + homeRouteForRole(demoRole);
        return;
      }

      clearSession();
      dataMode = "api";
      var button = document.querySelector("[data-login-submit]");
      if (button) { button.disabled = true; button.textContent = "Signing in..."; }
      window.CourtApi.login(email, password).then(function (result) {
        if (!result || !result.access_token) throw new Error("The Auth Service did not return an access token.");
        window.CourtApi.setAccessToken(result.access_token);
        return window.CourtApi.get("/api/v1/users/me");
      }).then(function (user) {
        var role = String(user && user.role || "").toUpperCase();
        var route = authUtils.homeRouteForRole(role);
        if (!route) throw new Error("This Management Web is available to OWNER and ADMIN accounts only.");
        authUser = user;
        demoRole = "";
        dataMode = "api";
        authMessage = "";
        loginEmailValue = "";
        location.hash = "#" + route;
      }).catch(function (error) {
        window.CourtApi.clearAccessToken();
        authUser = null;
        demoRole = "";
        if (error.status === 401) authMessage = "Email or password is incorrect, or the account is inactive.";
        else if (error.status === 0) authMessage = "Could not connect. Check your connection and try again.";
        else if (error.status === 502 || error.status === 503) authMessage = "Sign-in is temporarily unavailable. Please try again.";
        else authMessage = error.message || "Could not sign in.";
        renderLogin();
      });
    });
  }
  function renderShell(content, admin, active) {
    var nav = admin ? adminNav : ownerNav;
    var name = authUser ? (authUser.full_name || authUser.email || (admin ? "Administrator" : "Court Owner")) : (demoRole === "ADMIN" ? "Demo Administrator" : "Demo Owner");
    var email = authUser && authUser.email ? authUser.email : (demoRole ? "Demo account" : "");
    var initials = name.split(/\s+/).map(function (part) { return part.charAt(0); }).join("").slice(0, 2).toUpperCase();
    document.title = info[active][1] + " | Courtbook";
    document.getElementById("app").innerHTML =
      '<div class="app-shell"><aside class="sidebar" id="sidebar"><a class="brand text-decoration-none" href="' + routeLink(admin ? "admin-dashboard" : "dashboard") + '">' +
      '<span class="brand-mark"><i class="bi bi-trophy"></i></span><span>Courtbook<small>Management</small></span></a><div class="side-label">' +
      (admin ? "Administration" : "Operations") + '</div><nav class="side-nav">' + navMarkup(nav, active) + '</nav><div class="side-spacer"></div>' +
      '<a class="side-link" href="#/login" data-logout><i class="bi bi-box-arrow-left"></i><span>Sign out</span></a><div class="side-user"><span class="avatar">' +
      esc(initials) + '</span><span><strong>' + esc(name) + "</strong><small>" + esc(email || (admin ? "Administrator" : "Court Owner")) +
      '</small></span></div></aside><button class="mobile-backdrop" id="mobile-backdrop" aria-label="Close navigation"></button>' +
      '<div class="main-column"><header class="topbar"><button class="icon-button mobile-menu" id="menu-toggle" aria-label="Open navigation"><i class="bi bi-list"></i></button>' +
      '<div class="top-user"><span class="avatar">' + esc(initials) + '</span><div><strong>' + esc(name) + "</strong><small>" +
      esc(authUser ? (authUser.role + " account") : (admin ? "Demo Administrator" : "Demo Owner account")) + '</small></div></header><main class="page-content">' + content +
      '<footer class="page-footer">Sports Court Booking · Management workspace</footer></main></div></div>';
    document.getElementById("menu-toggle").addEventListener("click", function () { toggleMenu(true); });
    document.getElementById("mobile-backdrop").addEventListener("click", function () { toggleMenu(false); });
    var logout = document.querySelector("[data-logout]");
    if (logout) logout.addEventListener("click", function (event) {
      event.preventDefault();
      function finishLogout() {
        clearSession();
        dataMode = "api";
        authMessage = "";
        location.hash = "#/login";
      }
      if (currentRoute() === "qr-checkin" && (qrScanner || scannerInstance || scannerStarting)) {
        stopQrScanner().then(function (stopped) {
          if (stopped) finishLogout();
          else toast("Camera cleanup failed. Stop the camera before signing out.");
        });
      } else finishLogout();
    });
  }
  function toggleMenu(open) {
    document.getElementById("sidebar").classList.toggle("open", open);
    document.getElementById("mobile-backdrop").classList.toggle("open", open);
  }
  function heading(active, action) {
    var item = info[active];
    var title = active === "dashboard" && authUser && authUser.full_name ? "Welcome back, " + authUser.full_name : item[1];
    var headingClass = active === "owner-bookings" ? " page-heading--bookings" : "";
    return '<div class="page-heading' + headingClass + '"><div><p class="eyebrow">' + item[0] + "</p><h1>" + esc(title) + "</h1><p>" + item[2] + "</p></div>" + (action || "") + "</div>";
  }
  function actionButton(label, icon, message, outline) {
    return '<button class="btn ' + (outline ? "btn-outline-secondary" : "btn-success") + '" data-toast="' + message + '"><i class="bi ' + icon + ' me-1"></i><span class="desktop-button-text">' + label + "</span></button>";
  }
  function stats(type, values, live, unavailable) {
    var set = statSets[type] || statSets.dashboard;
    var ownerDemo = live && dataMode === "demo" && ["dashboard", "venues", "schedule"].indexOf(currentRoute()) >= 0;
    return '<div class="stat-grid">' + values.map(function (value, i) {
      var unavailableNote = Array.isArray(unavailable) ? unavailable[i] : (unavailable ? "Not available yet" : "");
      var note = unavailableNote || (ownerDemo || dataMode === "demo" ? "Demo data" : (live ? "Current catalogue" : "Demo data"));
      return '<article class="stat-card ' + ((type === "admin-dashboard" || type === "admin-dashboard-demo") && i === 3 ? "admin-highlight" : "") + '"><div class="stat-top"><span>' +
        esc(set[i][1]) + '</span><span class="stat-icon"><i class="bi ' + set[i][0] + '"></i></span></div><div class="stat-value">' + esc(value) +
        '</div><div class="stat-note">' + esc(note) + '</div></article>';
    }).join("") + "</div>";
  }
  function demoAccountStats() {
    var accounts = data.people;
    return [
      accounts.length,
      accounts.filter(function (row) { return row[3] === "User"; }).length,
      accounts.filter(function (row) { return row[3] === "Court Owner"; }).length,
      accounts.filter(function (row) { return row[5] === "Pending"; }).length
    ];
  }
  function demoBookingStats() {
    var bookings = data.adminBookings;
    var amount = bookings.reduce(function (total, row) {
      return total + Number(String(row[5]).replace(/[^0-9]/g, ""));
    }, 0);
    return [bookings.length, amount.toLocaleString("en-US") + " VND", bookings.filter(function (row) { return row[6] === "Checked in"; }).length, bookings.filter(function (row) { return row[6] === "Pending"; }).length];
  }
  function badge(status) {
    var value = String(status).toLowerCase(), style = "neutral";
    if (["confirmed", "checked in", "completed", "active", "open", "verified"].indexOf(value) >= 0) style = "";
    if (["pending", "review", "manual"].indexOf(value) >= 0) style = "warning";
    if (["cancelled", "inactive", "suspended"].indexOf(value) >= 0) style = "danger";
    return '<span class="badge-soft ' + style + '">' + esc(status) + "</span>";
  }
  function table(headers, rows) {
    var header = headers.map(function (value) { return "<th>" + value + "</th>"; }).join("");
    var body = rows.map(function (row) {
      return "<tr>" + row.map(function (cell, index) {
        return index === row.length - 1 ? "<td>" + badge(cell) + "</td>" : '<td class="' + (index === 0 ? "table-primary-text" : "") + '">' + esc(cell) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    return '<div class="table-wrap"><table class="table"><thead><tr>' + header + "</tr></thead><tbody>" + body + "</tbody></table></div>";
  }
  function panel(title, body, subtitle, action, extraClass) {
    return '<section class="panel-card' + (extraClass ? " " + extraClass : "") + '"><div class="panel-head"><div><h2>' + title + "</h2>" + (subtitle ? "<p>" + subtitle + "</p>" : "") + "</div>" + (action || "") + "</div>" + body + "</section>";
  }
  function bookingRows(admin) { return admin ? data.adminBookings : data.ownerBookings; }
  function dashboard(active) {
    var resources = currentResources(active !== "admin-dashboard" || dataMode === "demo");
    var sports = resources.sports;
    var venues = resources.venues;
    var courts = resources.courts;
    var slots = resources.slots;
    if (active === "admin-dashboard") {
      var activeSlots = slots.status === "loaded" ? slots.data.filter(function (slot) { return slot.is_active; }).length : "?";
      var accountStats = demoAccountStats();
      var bookingStats = demoBookingStats();
      var dashboardValues = dataMode === "demo"
        ? [accountStats[0], accountStats[2], bookingStats[0], bookingStats[1]]
        : ["—", adminCatalogueSummary.data ? adminCatalogueSummary.data.venues.total : "—", adminCatalogueSummary.data ? adminCatalogueSummary.data.courts.total : "—", "—"];
      var dashboardNotes = dataMode === "demo" ? false : [
        "Not available yet",
        adminCatalogueSummary.status === "loaded" ? "Court catalogue" : (adminCatalogueSummary.status === "loading" ? "Loading" : "Not available"),
        adminCatalogueSummary.status === "loaded" ? "Court catalogue" : (adminCatalogueSummary.status === "loading" ? "Loading" : "Not available"),
        "Not available yet"
      ];
      var catalogueSummaryBody;
      if (dataMode === "demo") {
        catalogueSummaryBody = '<div class="panel-body"><p class="mb-2">Sports: ' + sports.data.length + '</p><p class="mb-2">Venues: ' + venues.data.length + '</p><p class="mb-2">Courts: ' + courts.data.length + '</p><p class="mb-0">Active time slots: ' + activeSlots + '</p></div>';
      } else if (adminCatalogueSummary.status === "loading" || adminCatalogueSummary.status === "idle") {
        catalogueSummaryBody = '<div class="panel-body text-secondary" role="status">Loading catalogue summary...</div>';
      } else if (adminCatalogueSummary.status === "error") {
        catalogueSummaryBody = '<div class="panel-body"><div class="alert alert-warning mb-0" role="status">Catalogue totals are unavailable. ' + esc(adminCatalogueSummary.error) + '</div></div>';
      } else {
        var summary = adminCatalogueSummary.data;
        catalogueSummaryBody = '<div class="panel-body"><p class="mb-2">Sports: ' + summary.sports.total + ' (' + summary.sports.active + ' active)</p><p class="mb-2">Venues: ' + summary.venues.total + ' (' + summary.venues.active + ' active)</p><p class="mb-2">Courts: ' + summary.courts.total + ' (' + summary.courts.active + ' active)</p><p class="mb-0">Time slots: ' + summary.time_slots.total + ' (' + summary.time_slots.active + ' active)</p></div>';
      }
      return heading(active, '<button class="btn btn-outline-secondary" data-court-refresh><i class="bi bi-arrow-clockwise me-1"></i>Refresh</button>') +
        (dataMode === "demo" ? demoNotice("Dashboard figures are sample data. The catalogue below reflects the selected data source.") : '<p class="text-secondary small">Account and booking summaries are not available yet.</p>') +
        stats(dataMode === "demo" ? "admin-dashboard-demo" : "admin-dashboard", dashboardValues, false, dashboardNotes) +
        (dataMode === "demo" ? '<p class="text-secondary small">Sample totals: ' + accountStats[1] + ' users, ' + accountStats[3] + ' owners pending review, ' + bookingStats[2] + ' checked-in bookings, ' + bookingStats[3] + ' pending bookings.</p>' : "") +
        (anyAdminDataError(resources) ? resourceError("catalogue information", "One or more lists could not be loaded.") : "") +
        '<div class="content-grid">' + panel("Court catalogue", catalogueSummaryBody, dataMode === "demo" ? "Demo catalogue" : "Current catalogue") +
        '</div><div class="mt-3 d-flex gap-2"><a class="btn btn-outline-secondary btn-sm" href="#/admin-venues">Open venue registry</a><a class="btn btn-outline-secondary btn-sm" href="#/admin-bookings">Open bookings</a></div>';
    }
    var activeSlots = slots.status === "loaded" ? slots.data.filter(function (slot) { return slot.is_active; }).length : "?";
    var values = [
      sports.status === "loaded" ? sports.data.length : "?",
      venues.status === "loaded" ? venues.data.length : "?",
      courts.status === "loaded" ? courts.data.length : "?",
      activeSlots
    ];
    var venueBody;
    if (venues.status === "loading" || venues.status === "idle") venueBody = '<div class="panel-body">Loading venue data...</div>';
    else if (venues.status === "error") venueBody = '<div class="panel-body">' + resourceError("venues", venues.error) + "</div>";
    else if (!venues.data.length) venueBody = '<div class="panel-body text-secondary">No venues found.</div>';
    else {
      venueBody = '<div class="table-wrap"><table class="table"><thead><tr><th>Venue</th><th>Address</th><th>Courts</th><th>Status</th><th></th></tr></thead><tbody>' +
        venues.data.slice(0, 6).map(function (venue) {
          var linkedCourts = courts.status === "loaded" ? courts.data.filter(function (court) { return court.venue_id === venue.id; }).length : "?";
          return '<tr><td class="table-primary-text">' + esc(venue.name) + '</td><td>' + esc(venue.address) + '</td><td>' + esc(linkedCourts) + '</td><td>' + courtStatus(venue.is_active) + '</td><td>' + detailButton("venues", venue.id) + '</td></tr>';
        }).join("") + '</tbody></table></div>';
    }
    var anyError = Object.keys(resources).some(function (key) { return resources[key].status === "error"; });
    var gatewayError = anyError && Object.keys(resources).some(function (key) { return resources[key].status === "error" && /failed to fetch|networkerror|connection refused|load failed/i.test(resources[key].error); });
    return heading(active, '<button class="btn btn-outline-secondary" data-court-refresh><i class="bi bi-arrow-clockwise me-1"></i>Refresh</button>') +
      stats("court-overview", values, true) +
      '<p class="text-secondary small">' + (dataMode === "demo" ? "Sample counts are for preview only. " : "Counts reflect the catalogue shown here. ") + 'Active slots are schedule entries, not booking availability.</p>' +
      (anyError ? (gatewayError ? resourceError("catalogue information", "Could not load the latest information." ) : resourceError("catalogue information", "One or more lists could not be loaded.")) : "") +
      '<div class="content-grid">' + panel("Venue catalogue", venueBody, dataMode === "demo" ? "Demo data" : "Your venues") +
      panel("Court data", '<div class="panel-body"><p class="mb-2">Sports: ' + (sports.status === "loaded" ? sports.data.length : "?") + '</p><p class="mb-2">Venues: ' + (venues.status === "loaded" ? venues.data.length : "?") + '</p><p class="mb-2">Courts: ' + (courts.status === "loaded" ? courts.data.length : "?") + '</p><p class="mb-0">Active time slots: ' + activeSlots + '</p></div>', "Sports, venues, courts, and schedules") +
      '</div><div class="mt-3 d-flex gap-2"><a class="btn btn-outline-secondary btn-sm" href="#/venues">Open venues and courts</a><a class="btn btn-outline-secondary btn-sm" href="#/schedule">Open schedule</a></div>';
  }
  function anyAdminDataError(resources) {
    return Object.keys(resources).some(function (key) { return resources[key].status === "error"; });
  }
  function bookingPage(active, admin) {
    if (admin) {
      if (dataMode !== "demo") {
        var filters = '<div class="toolbar admin-filter-toolbar"><input class="form-control" type="search" data-admin-booking-id value="' + esc(adminBookingsFilters.booking_id) + '" placeholder="Booking ID" aria-label="Search by booking ID"><select class="form-select" data-admin-booking-status aria-label="Filter status"><option value="">All statuses</option>' + ["PENDING", "CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "EXPIRED"].map(function (status) { return '<option value="' + status + '" ' + (adminBookingsFilters.status === status ? "selected" : "") + '>' + status + '</option>'; }).join("") + '</select>' + [["venue_id", "Venue ID"], ["court_id", "Court ID"], ["owner_id", "Owner ID"], ["user_id", "User ID"]].map(function (field) { return '<input class="form-control" type="number" min="1" data-admin-booking-field="' + field[0] + '" value="' + esc(adminBookingsFilters[field[0]]) + '" placeholder="' + field[1] + '" aria-label="Filter ' + field[1] + '">'; }).join("") + calendarPickerMarkup("admin-bookings-from", "Date from", adminBookingsFilters.date_from, { filterAttribute: ' data-admin-date-filter="bookings" data-admin-date-field="date_from"' }) + calendarPickerMarkup("admin-bookings-to", "Date to", adminBookingsFilters.date_to, { filterAttribute: ' data-admin-date-filter="bookings" data-admin-date-field="date_to"' }) + '<button class="btn btn-outline-secondary" type="button" data-admin-filter-clear="bookings">Clear filters</button></div>';
        var content = adminListState(adminBookingsState);
        if (adminBookingsState.status === "loaded" && adminBookingsState.data.items.length) {
          var rows = adminBookingsState.data.items.map(function (booking) {
            return '<tr><td class="table-primary-text">' + esc(booking.id) + '</td><td>' + esc(booking.user_id) + '</td><td>' + esc(booking.owner_id) + '</td><td>' + esc(booking.venue_id) + '</td><td>' + esc(booking.court_id) + '</td><td>' + apiDate(booking.slot_date) + '</td><td>' + statusBadge(booking.status) + '</td><td>' + esc(booking.total_amount) + '</td><td class="table-actions"><button class="btn btn-sm btn-outline-secondary" type="button" data-admin-booking-detail="' + esc(booking.id) + '">Details</button></td></tr>';
          }).join("");
          content = '<div class="table-wrap"><table class="table"><thead><tr><th>Booking</th><th>User</th><th>Owner</th><th>Venue</th><th>Court</th><th>Date</th><th>Status</th><th>Amount</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>' + adminPagination("bookings", adminBookingsState.data);
        }
        return heading(active) + panel("Bookings", filters + content, "System-wide booking records · read-only");
      }
      var adminRows = bookingRows(true);
      return heading(active, actionButton("Export bookings", "bi-download", "Sample booking list exported.", true)) + demoNotice("Sample bookings are shown for preview only.") +
        stats("admin-bookings", demoBookingStats()) + panel("All bookings", '<div class="toolbar admin-filter-toolbar" data-filter-toolbar><input class="form-control" type="search" data-table-search data-admin-search placeholder="Search booking, customer or venue" aria-label="Search bookings"><select class="form-select" data-status-filter aria-label="Filter booking status"><option value="">All statuses</option><option>Confirmed</option><option>Checked in</option><option>Pending</option><option>Completed</option><option>Cancelled</option></select><button class="btn btn-outline-secondary" type="button" data-filter-reset>Reset filters</button></div>' + table(["Booking ID", "Customer", "Venue", "Court", "Start time", "Amount", "Status"], adminRows) + '<div class="table-foot" data-filter-count>Showing ' + adminRows.length + ' records</div>', "Admin sample screen; search and status filters affect only these fictional rows");
    }
    if (dataMode !== "demo") {
      var venueOptions = ownerBookingVenueIds.map(function (id) {
        return '<option value="' + esc(id) + '" ' + (bookingVenueId === String(id) ? "selected" : "") + '>Venue #' + esc(id) + '</option>';
      }).join("");
      var apiToolbar = '<div class="toolbar booking-filter-toolbar"><input class="form-control" type="search" data-booking-search value="' + esc(bookingSearch) + '" placeholder="Search booking, user, venue or court ID" aria-label="Search booking details">' +
        '<select class="form-select" data-booking-venue aria-label="Filter by venue"><option value="">All venues</option>' + venueOptions + '</select>' +
        calendarPickerMarkup("booking-filter", "Filter booking date", bookingDate) + '<select class="form-select" data-booking-status aria-label="Filter booking status"><option value="">All statuses</option>' +
        ["PENDING", "CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "EXPIRED"].map(function (status) { return '<option value="' + status + '" ' + (bookingStatus === status ? "selected" : "") + '>' + status + '</option>'; }).join("") +
        '</select><button class="btn btn-outline-secondary" type="button" data-booking-clear>Clear filters</button></div>';
      var bookingRefreshAction = '<div class="page-heading-actions booking-header-actions"><button class="btn btn-outline-secondary" type="button" data-booking-retry ' + (ownerBookingsState.status === "loading" ? "disabled" : "") + '><i class="bi bi-arrow-clockwise me-1"></i>Refresh</button></div>';
      var apiContent = "";
      if (ownerBookingsState.status === "idle" || ownerBookingsState.status === "loading") {
        apiContent = '<div class="panel-body text-secondary" role="status">Loading bookings...</div>';
      } else if (ownerBookingsState.status === "error") {
        apiContent = '<div class="panel-body"><div class="alert alert-danger mb-0" role="alert">' + esc(ownerBookingErrorMessage(ownerBookingsState.error)) + ' <button class="btn btn-sm btn-outline-danger ms-2" type="button" data-booking-retry>Retry</button></div></div>';
      } else {
        var apiBookings = filteredOwnerBookings();
        if (!ownerBookingsState.data.length) {
          var filtersActive = bookingVenueId || bookingDate || bookingStatus;
          apiContent = '<div class="panel-body text-secondary" role="status">' + (filtersActive ? "No bookings match these filters." : "No bookings are available for your venues.") + '</div>';
        } else apiContent = '<div class="table-wrap booking-list-table-wrap"><table class="table booking-list-table"><thead><tr><th>Booking ID</th><th>User ID</th><th>Venue</th><th>Court</th><th>Date</th><th>Time</th><th>Total amount</th><th>Status</th><th>Actions</th></tr></thead><tbody id="owner-booking-rows" aria-live="polite">' + ownerBookingRowsMarkup(apiBookings) + '</tbody></table></div><div class="table-foot" data-booking-count>Showing ' + apiBookings.length + ' of ' + ownerBookingsState.data.length + ' bookings</div>';
      }
      return heading(active, bookingRefreshAction) + bookingModeNotice() + panel("Owner bookings", apiToolbar + apiContent, "Manage court reservations", "", "calendar-panel-card");
    }
    var filtered = filteredDemoBookings();
    var body = '<div class="toolbar booking-filter-toolbar"><input class="form-control" type="search" data-booking-search value="' + esc(bookingSearch) + '" placeholder="Search booking ID or customer" aria-label="Search booking ID or customer">' +
      calendarPickerMarkup("booking-filter", "Filter booking date", bookingDate) + '<select class="form-select" data-booking-status aria-label="Filter booking status"><option value="">All statuses</option>' +
      ["PENDING", "CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "EXPIRED"].map(function (status) { return '<option value="' + status + '" ' + (bookingStatus === status ? "selected" : "") + '>' + status + '</option>'; }).join("") +
      '</select><button class="btn btn-outline-secondary" data-booking-clear>Clear filters</button></div><div class="table-wrap booking-list-table-wrap"><table class="table booking-list-table"><thead><tr><th>Booking ID</th><th>Customer</th><th>Venue</th><th>Court</th><th>Date</th><th>Time</th><th>Total Amount</th><th>Status</th><th>Actions</th></tr></thead><tbody id="owner-booking-rows" aria-live="polite">' +
      bookingRowsMarkup(filtered) + '</tbody></table></div><div class="table-foot" data-booking-count>Showing ' + filtered.length + ' of ' + demoBookings.length + ' Demo bookings - newest first</div>';
    return heading(active) + bookingModeNotice() + demoNotice("Sample booking information is fictional and remains in browser memory only.") + panel("Owner bookings", body, "Filter bookings and open a booking for details", "", "calendar-panel-card");
  }
  function filteredDemoBookings() {
    var query = bookingSearch.trim().toLowerCase();
    return demoBookings.slice().sort(function (a, b) { return b.created_at.localeCompare(a.created_at); }).filter(function (booking) {
      return (!query || booking.id.toLowerCase().indexOf(query) >= 0 || booking.customer.name.toLowerCase().indexOf(query) >= 0) &&
        (!bookingDate || booking.date === bookingDate) && (!bookingStatus || booking.status === bookingStatus);
    });
  }
  function loadOwnerBookings() {
    if (dataMode === "demo" || !authUser || authUser.role !== "OWNER") return Promise.resolve([]);
    var requestId = ++ownerBookingsRequestId;
    ownerBookingsState = { status: "loading", data: ownerBookingsState.data, error: "" };
    render();
    return window.OwnerBookingsApi.list({ venue_id: bookingVenueId, date: bookingDate, status: bookingStatus }).then(function (bookings) {
      if (!Array.isArray(bookings)) throw new Error("The booking list could not be read.");
      if (requestId !== ownerBookingsRequestId) return [];
      bookings.forEach(function (booking) {
        if (booking && Number.isInteger(Number(booking.venue_id)) && !ownerBookingVenueIds.includes(Number(booking.venue_id))) ownerBookingVenueIds.push(Number(booking.venue_id));
      });
      ownerBookingVenueIds.sort(function (left, right) { return left - right; });
      ownerBookingsState = { status: "loaded", data: bookings, error: "" };
      render();
      return bookings;
    }).catch(function (error) {
      if (requestId === ownerBookingsRequestId) {
        ownerBookingsState = { status: "error", data: [], error: error };
        render();
      }
      return [];
    });
  }
  function filteredOwnerBookings() {
    var query = bookingSearch.trim().toLowerCase();
    return ownerBookingsState.data.filter(function (booking) {
      var text = [booking.id, booking.user_id, booking.venue_id, booking.court_id, booking.time_slot_id].join(" ").toLowerCase();
      return !query || text.indexOf(query) >= 0;
    });
  }
  function ownerBookingRowsMarkup(bookings) {
    if (!bookings.length) return '<tr><td colspan="9" class="text-secondary">No bookings match this search.</td></tr>';
    return bookings.map(function (booking) {
      var complete = booking.status === "CHECKED_IN" ? '<button class="btn btn-sm btn-success" type="button" data-booking-complete="' + esc(booking.id) + '" ' + (ownerBookingCompletionPending ? "disabled" : "") + '>Complete Booking</button>' : "";
      return '<tr><td class="table-primary-text">' + esc(booking.id) + '</td><td>' + esc(booking.user_id) + '</td><td>Venue #' + esc(booking.venue_id) + '</td><td>Court #' + esc(booking.court_id) + '</td><td>' + apiDate(booking.slot_date) + '</td><td>' + apiTime(booking.start_time) + ' - ' + apiTime(booking.end_time) + '</td><td>' + esc(formatBookingAmount(Number(booking.total_amount))) + '</td><td>' + statusBadge(booking.status) + '</td><td class="table-actions"><div class="table-action-group"><button class="btn btn-sm btn-outline-secondary" type="button" data-booking-detail="' + esc(booking.id) + '">Details</button>' + complete + '</div></td></tr>';
    }).join("");
  }
  function bookingRowsMarkup(bookings) {
    if (!bookings.length) return '<tr><td colspan="9" class="text-secondary">No bookings match these filters.</td></tr>';
    return bookings.map(function (booking) {
      return '<tr><td class="table-primary-text">' + esc(booking.id) + '</td><td>' + esc(booking.customer.name) + '</td><td>' + esc(booking.venue) + '</td><td>' + esc(booking.court) + '</td><td>' + apiDate(booking.date) + '</td><td>' + esc(booking.start_time + " - " + booking.end_time) + '</td><td>' + esc(formatBookingAmount(booking.total_amount)) + '</td><td>' + statusBadge(booking.status) + '</td><td class="table-actions"><div class="table-action-group"><button class="btn btn-sm btn-outline-secondary" data-booking-detail="' + esc(booking.id) + '">Details</button>' +
        (booking.status === "CHECKED_IN" ? '<button class="btn btn-sm btn-success" data-booking-complete="' + esc(booking.id) + '">Complete Booking</button>' : "") + '</div></td></tr>';
    }).join("");
  }
  function applyBookingFilters() {
    var rows = document.getElementById("owner-booking-rows");
    if (!rows) return;
    bookingSearch = (document.querySelector("[data-booking-search]") || {}).value || "";
    if (dataMode !== "demo") {
      var apiBookings = filteredOwnerBookings();
      rows.innerHTML = ownerBookingRowsMarkup(apiBookings);
      var apiCount = document.querySelector("[data-booking-count]");
      if (apiCount) apiCount.textContent = "Showing " + apiBookings.length + " of " + ownerBookingsState.data.length + " bookings";
      return;
    }
    var bookingDateInput = document.querySelector("[data-booking-date]");
    bookingDate = bookingDateInput ? bookingDateInput.dataset.dateValue || "" : "";
    bookingStatus = (document.querySelector("[data-booking-status]") || {}).value || "";
    var filtered = filteredDemoBookings();
    rows.innerHTML = bookingRowsMarkup(filtered);
    var count = document.querySelector("[data-booking-count]");
    if (count) count.textContent = "Showing " + filtered.length + " of " + demoBookings.length + " Demo bookings - newest first";
  }
  function bookingModeNotice() {
    return dataMode === "demo"
      ? '<div class="alert alert-warning py-2 small" role="status"><strong>Demo:</strong> Sample bookings are shown for preview.</div>'
      : '<div class="alert alert-info py-2 small" role="status">Manage court reservations.</div>';
  }
  function ownerBookingErrorMessage(error) {
    var status = error && error.status;
    if (status === 401) return "Your session expired or you are not signed in. Sign in again.";
    if (status === 403) return "This account does not have Owner permission to view these bookings.";
    if (status === 404) return "Booking was not found or is outside your Owner access.";
    if (status === 409) return "Booking is no longer in a state that allows this action.";
    if (status === 422) return "The booking filters or request are invalid. Check them and try again.";
    if (status === 503) return "Booking information is temporarily unavailable.";
    if (status === 504) return "This request took too long. Try again.";
    if (status === 0) return "Could not connect. Try again in a moment.";
    return "Could not complete this request. Try again.";
  }
  function loadOwnerBookingDetail(bookingId) {
    toast("Loading booking details...");
    return window.OwnerBookingsApi.detail(bookingId).then(function (booking) {
      bookingDetail(booking);
    }).catch(function (error) {
      toast(ownerBookingErrorMessage(error));
    });
  }
  function refreshOwnerBookingAfterCompletion(bookingId) {
    return loadOwnerBookings().then(function () {
      return window.OwnerBookingsApi.detail(bookingId);
    }).then(function (booking) {
      bookingDetail(booking);
    });
  }
  function completeOwnerBooking(booking, button) {
    if (!booking || booking.status !== "CHECKED_IN") {
      toast("Only CHECKED_IN bookings can be completed.");
      return;
    }
    if (ownerBookingCompletionPending) return;
    if (!window.confirm("Complete booking " + booking.id + "?")) return;
    ownerBookingCompletionPending = true;
    if (button) { button.disabled = true; button.textContent = "Completing..."; }
    window.OwnerBookingsApi.complete(booking.id).then(function () {
      toast("Booking completed.");
      return refreshOwnerBookingAfterCompletion(booking.id);
    }).catch(function (error) {
      toast(ownerBookingErrorMessage(error));
      if (error && error.status === 409) {
        loadOwnerBookings().then(function () {
          return window.OwnerBookingsApi.detail(booking.id);
        }).then(bookingDetail).catch(function () {});
      }
    }).finally(function () {
      ownerBookingCompletionPending = false;
      if (currentRoute() === "owner-bookings" && dataMode !== "demo") render();
    });
  }
  function formatBookingAmount(value) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(value);
  }
  function statusBadge(status) {
    var styles = { PENDING: "warning", CONFIRMED: "", CHECKED_IN: "", COMPLETED: "", CANCELLED: "danger", EXPIRED: "danger" };
    return '<span class="badge-soft ' + (styles[status] || "neutral") + '">' + esc(status) + '</span>';
  }
  function bookingDetail(booking) {
    var apiBooking = dataMode !== "demo";
    var customerRows = apiBooking ? [["User ID", booking.user_id]] : [["Name", booking.customer.name]];
    if (!apiBooking && booking.customer.email) customerRows.push(["Email", booking.customer.email]);
    if (!apiBooking && booking.customer.phone) customerRows.push(["Phone", booking.customer.phone]);
    var bookingRows = apiBooking
      ? [["Venue ID", booking.venue_id], ["Court ID", booking.court_id], ["Time Slot ID", booking.time_slot_id], ["Date", apiDate(booking.slot_date)], ["Time", booking.start_time + " - " + booking.end_time], ["Total amount", formatBookingAmount(Number(booking.total_amount))]]
      : [["Venue", booking.venue], ["Court", booking.court], ["Date", apiDate(booking.date)], ["Time", booking.start_time + " - " + booking.end_time], ["Total amount", formatBookingAmount(booking.total_amount)]];
    if (apiBooking && booking.expires_at) bookingRows.push(["Expires at", booking.expires_at]);
    if (apiBooking && booking.created_at) bookingRows.push(["Created at", booking.created_at]);
    var statusRows = [];
    if (!apiBooking && booking.payment_status) statusRows.push(["Payment", booking.payment_status]);
    if (!apiBooking && booking.checkin_status) statusRows.push(["QR check-in", booking.checkin_status]);
    function detailSection(title, rows) {
      return '<section class="booking-detail-section"><h3>' + title + '</h3><div class="booking-detail-grid">' + rows.map(function (row) {
        return '<div class="detail-row"><span>' + esc(row[0]) + '</span><strong>' + esc(row[1]) + '</strong></div>';
      }).join("") + '</div></section>';
    }
    var host = document.getElementById("booking-detail-modal-host");
    if (!host) { host = document.createElement("div"); host.id = "booking-detail-modal-host"; document.body.appendChild(host); }
    host.innerHTML = '<div class="modal fade" id="booking-detail-modal" tabindex="-1" aria-labelledby="booking-detail-title" aria-hidden="true"><div class="modal-dialog modal-dialog-centered modal-dialog-scrollable booking-detail-modal"><div class="modal-content"><div class="modal-header align-items-start"><div><p class="eyebrow mb-1">Booking details</p><h2 class="modal-title fs-6" id="booking-detail-title">' + esc(booking.id) + '</h2></div><div class="d-flex align-items-center gap-2">' + statusBadge(booking.status) + '<button type="button" class="btn-close ms-2" data-modal-close aria-label="Close"></button></div></div><div class="modal-body">' + detailSection("Customer", customerRows) + detailSection("Court and booking", bookingRows) + (statusRows.length ? detailSection("Payment and check-in", statusRows) : "") + '</div><div class="modal-footer">' + (booking.status === "CHECKED_IN" ? '<button type="button" class="btn btn-success" data-booking-complete="' + esc(booking.id) + '">Complete Booking</button>' : "") + '</div></div></div></div>';
    var modal = document.getElementById("booking-detail-modal");
    var completeButton = modal.querySelector("[data-booking-complete]");
    if (completeButton) completeButton.addEventListener("click", function () {
      if (apiBooking) completeOwnerBooking(booking, completeButton);
      else completeDemoBooking(booking.id);
    });
    showManagedModal(modal, host);
  }
  function showManagedModal(modal, host) {
    modal.addEventListener("hidden.bs.modal", function () { host.innerHTML = ""; }, { once: true });
    modal.addEventListener("click", function (event) {
      var target = event.target;
      if (!(target instanceof Element)) return;
      if (target === modal || target.closest("[data-modal-close]")) {
        event.preventDefault();
        closeManagedModal(modal);
      }
    });
    modal.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeManagedModal(modal);
      }
    });
    if (window.bootstrap && window.bootstrap.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(modal).show();
      modal.focus();
      return;
    }
    modal.classList.add("show");
    modal.style.display = "block";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.removeAttribute("aria-hidden");
    modal.focus();
  }
  function showAccountDetails(account) {
    var host = document.getElementById("admin-account-modal-host");
    if (!host) {
      host = document.createElement("div");
      host.id = "admin-account-modal-host";
      document.body.appendChild(host);
    }
    host.innerHTML = '<div class="modal fade" id="admin-account-modal" tabindex="-1" aria-labelledby="admin-account-title" aria-hidden="true"><div class="modal-dialog modal-dialog-centered"><div class="modal-content"><div class="modal-header"><div><p class="eyebrow mb-1">Demo account details</p><h2 class="modal-title fs-6" id="admin-account-title">' + esc(account[1]) + '</h2></div><button type="button" class="btn-close" data-modal-close aria-label="Close"></button></div><div class="modal-body"><div class="detail-row"><span>Account ID</span><strong>' + esc(account[0]) + '</strong></div><div class="detail-row"><span>Email</span><strong>' + esc(account[2]) + '</strong></div><div class="detail-row"><span>Role</span><strong>' + esc(account[3]) + '</strong></div><div class="detail-row"><span>Joined</span><strong>' + esc(account[4]) + '</strong></div><div class="detail-row"><span>Status</span><strong>' + esc(account[5]) + '</strong></div></div></div></div></div>';
    showManagedModal(document.getElementById("admin-account-modal"), host);
  }
  function showAdminRecordDetails(title, record, fields) {
    var host = document.getElementById("admin-record-modal-host");
    if (!host) { host = document.createElement("div"); host.id = "admin-record-modal-host"; document.body.appendChild(host); }
    var rows = fields.filter(function (field) { return record[field[0]] !== undefined && record[field[0]] !== null; }).map(function (field) {
      return '<div class="detail-row"><span>' + esc(field[1]) + '</span><strong>' + esc(record[field[0]]) + '</strong></div>';
    }).join("");
    host.innerHTML = '<div class="modal fade" id="admin-record-modal" tabindex="-1" aria-labelledby="admin-record-title" aria-hidden="true"><div class="modal-dialog modal-dialog-centered modal-dialog-scrollable"><div class="modal-content"><div class="modal-header"><h2 class="modal-title fs-6" id="admin-record-title">' + esc(title) + '</h2><button type="button" class="btn-close" data-modal-close aria-label="Close"></button></div><div class="modal-body">' + rows + '</div></div></div></div>';
    showManagedModal(document.getElementById("admin-record-modal"), host);
  }
  function closeManagedModal(modal) {
    if (window.bootstrap && window.bootstrap.Modal) {
      var instance = window.bootstrap.Modal.getInstance(modal);
      if (instance) instance.hide();
      return;
    }
    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    if (modal.parentElement) modal.parentElement.innerHTML = "";
  }
  function completeDemoBooking(id) {
    var booking = demoBookings.find(function (item) { return item.id === id; });
    if (!booking || booking.status !== "CHECKED_IN") { toast("Only CHECKED_IN bookings can be completed."); return; }
    if (dataMode !== "demo") { toast("Live check-in is not available here. No request was sent."); return; }
    if (!window.confirm("Complete booking " + booking.id + "?")) return;
    var modal = document.getElementById("booking-detail-modal");
    if (modal) closeManagedModal(modal);
    booking.status = "COMPLETED";
    render();
    toast("Demo booking completed. No API request was sent.");
  }
  function venuePage(active, admin) {
    var editable = !admin;
    var canManageDemo = editable && dataMode === "demo";
    var canManageApi = dataMode === "api" && authUser && window.CourtApi.hasAccessToken();
    var resources = currentResources(editable || dataMode === "demo");
    var venues = resources.venues;
    var courts = resources.courts;
    var sports = resources.sports;
    var sportCount = sports.status === "loaded" ? sports.data.length : "?";
    var venueCount = venues.status === "loaded" ? venues.data.length : "?";
    var courtCount = courts.status === "loaded" ? courts.data.length : "?";
    var activeVenueCount = venues.status === "loaded" ? venues.data.filter(function (venue) { return venue.is_active; }).length : "?";
    var tabs = [["sports", "Sports", sportCount], ["venues", "Venues", venueCount], ["courts", "Courts", courtCount]];
    var tabMarkup = '<div class="registry-tabs" role="tablist" aria-label="Sports, venues, and courts">' + tabs.map(function (tab) {
      return '<button type="button" class="registry-tab ' + (registryTab === tab[0] ? "active" : "") + '" role="tab" id="registry-tab-' + tab[0] + '" aria-selected="' + String(registryTab === tab[0]) + '" aria-controls="registry-panel" data-registry-tab="' + tab[0] + '">' + esc(tab[1]) + ' <span>' + esc(tab[2]) + '</span></button>';
    }).join("") + '</div>';
    var searchValue = registryTab === "sports" ? sportSearch : (registryTab === "venues" ? venueSearch : courtSearch);
    var searchPlaceholder = { sports: "Search sports", venues: "Search venues or addresses", courts: "Search courts, venues or sports" }[registryTab];
    var filters = "";
    if (registryTab === "sports") {
      filters = '<select class="form-select" data-registry-status data-focus-key="registry-status"><option value="">All statuses</option><option value="true" ' + (registryFilters.active === "true" ? "selected" : "") + '>Active</option><option value="false" ' + (registryFilters.active === "false" ? "selected" : "") + '>Inactive</option></select>';
    } else if (registryTab === "venues") {
      filters = '<select class="form-select" data-registry-sport-filter data-focus-key="registry-sport"><option value="">All sports</option>' + sports.data.map(function (sport) { return '<option value="' + esc(sport.id) + '" ' + (registryFilters.sportId === String(sport.id) ? "selected" : "") + '>' + esc(sport.name) + '</option>'; }).join("") + '</select><select class="form-select" data-registry-active-filter data-focus-key="registry-active"><option value="">All statuses</option><option value="true" ' + (registryFilters.active === "true" ? "selected" : "") + '>Active</option><option value="false" ' + (registryFilters.active === "false" ? "selected" : "") + '>Inactive</option></select>';
    } else {
      filters = '<select class="form-select" data-registry-sport-filter data-focus-key="registry-sport"><option value="">All sports</option>' + sports.data.map(function (sport) { return '<option value="' + esc(sport.id) + '" ' + (registryFilters.sportId === String(sport.id) ? "selected" : "") + '>' + esc(sport.name) + '</option>'; }).join("") + '</select><select class="form-select" data-registry-active-filter data-focus-key="registry-active"><option value="">All statuses</option><option value="true" ' + (registryFilters.active === "true" ? "selected" : "") + '>Active</option><option value="false" ' + (registryFilters.active === "false" ? "selected" : "") + '>Inactive</option></select><select class="form-select" data-registry-venue-filter data-focus-key="registry-venue"><option value="">All venues</option>' + venues.data.map(function (venue) { return '<option value="' + esc(venue.id) + '" ' + (registryFilters.venueId === String(venue.id) ? "selected" : "") + '>' + esc(venue.name) + '</option>'; }).join("") + '</select>';
    }
    var canManageRegistry = canManageDemo || (canManageApi && (authUser.role === "ADMIN" || (editable && authUser.role === "OWNER" && registryTab !== "sports")));
    var addButton = canManageRegistry ? crudOpenButton(registryTab, null, "Add " + registryTab.slice(0, -1), "btn-success") : "";
    var controls = '<div class="registry-toolbar registry-toolbar--' + registryTab + '"><div class="input-group registry-search"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-registry-search data-focus-key="registry-search" type="search" value="' + esc(searchValue) + '" placeholder="' + esc(searchPlaceholder) + '" aria-label="' + esc(searchPlaceholder) + '"></div>' + filters + addButton + '</div>';
    var form = canManageRegistry ? crudFormMarkup(registryTab, resources) : "";
    var content;
    if (registryTab === "sports") {
      var sportRows = sports.data.map(function (sport) {
        var actions = '<div class="table-action-group">' + detailButton("sports", sport.id);
        if (canManageDemo || (canManageApi && authUser.role === "ADMIN")) actions += '<div class="crud-actions">' + crudOpenButton("sports", sport.id, "Edit") + crudDeleteButton("sports", sport.id) + '</div>';
        actions += '</div>';
        return '<tr data-registry-row data-kind="sports" data-search="' + esc((sport.name + " " + (sport.description || "")).toLowerCase()) + '" data-active="' + String(!!sport.is_active) + '"><td class="table-primary-text">' + esc(sport.name) + '</td><td>' + esc(sport.description || "—") + '</td><td>' + courtStatus(sport.is_active) + '</td><td class="table-actions">' + actions + '</td></tr>';
      }).join("");
      content = '<div class="table-wrap"><table class="table"><thead><tr><th>Sport</th><th>Description</th><th>Status</th><th>Actions</th></tr></thead><tbody>' + (sportRows || '<tr><td colspan="4" class="text-secondary">No sports are listed.</td></tr>') + '</tbody></table></div>';
    } else if (registryTab === "venues") {
      var venueCards = venues.data.map(function (venue) {
        var linkedCourts = courts.status === "loaded" ? courts.data.filter(function (court) { return court.venue_id === venue.id; }) : [];
        var sportNames = [];
        linkedCourts.forEach(function (court) {
          var sport = sports.data.find(function (item) { return item.id === court.sport_id; });
          if (sport && sportNames.indexOf(sport.name) < 0) sportNames.push(sport.name);
        });
        var ownerLabel = dataMode === "demo" && editable ? "Demo session" : (venue.owner_id ? "Owner #" + venue.owner_id : "Owner unavailable");
        var actions = '<div class="table-action-group">' + detailButton("venues", venue.id, "Details");
        if (canManageDemo || canManageApi) actions += '<div class="crud-actions">' + crudOpenButton("venues", venue.id, "Edit") + crudDeleteButton("venues", venue.id) + '</div>';
        actions += '</div>';
        return '<article class="venue-card" data-registry-row data-kind="venues" data-search="' + esc((venue.name + " " + venue.address).toLowerCase()) + '" data-sport-ids="' + esc(linkedCourts.map(function (court) { return "|" + court.sport_id + "|"; }).join("")) + '" data-active="' + String(!!venue.is_active) + '"><div class="venue-cover"><span class="venue-cover-icon"><i class="bi bi-building"></i></span>' + courtStatus(venue.is_active) + '</div><div class="venue-body"><h3>' + esc(venue.name) + '</h3><p><i class="bi bi-geo-alt me-1"></i>' + esc(venue.address) + '</p><div class="venue-meta"><span><strong>' + linkedCourts.length + '</strong> courts</span><span>' + esc(sportNames.join(", ") || "No linked sports") + '</span></div><div class="detail-row"><span>Owner</span><strong>' + esc(ownerLabel) + '</strong></div><div class="registry-row-actions">' + actions + '</div></div></article>';
      }).join("");
      content = '<div class="venue-grid">' + (venueCards || '<p class="panel-body text-secondary">No venues are available in this data source.</p>') + '</div>';
    } else {
      var courtRows = courts.data.map(function (court) {
        var venue = venues.data.find(function (item) { return item.id === court.venue_id; });
        var sport = sports.data.find(function (item) { return item.id === court.sport_id; });
        var searchText = [court.name, venue && venue.name, sport && sport.name].filter(Boolean).join(" ").toLowerCase();
        var actions = '<div class="table-action-group">' + detailButton("courts", court.id);
        if (canManageDemo || canManageApi) actions += '<div class="crud-actions">' + crudOpenButton("courts", court.id, "Edit") + crudDeleteButton("courts", court.id) + '</div>';
        actions += '</div>';
        return '<tr data-registry-row data-kind="courts" data-search="' + esc(searchText) + '" data-venue-id="' + esc(court.venue_id) + '" data-sport-id="' + esc(court.sport_id) + '" data-active="' + String(!!court.is_active) + '"><td class="table-primary-text">' + esc(court.name) + '</td><td>' + esc(venue ? venue.name : "Venue #" + court.venue_id) + '</td><td>' + esc(sport ? sport.name : "Sport #" + court.sport_id) + '</td><td>' + formatPriceVnd(court.price_per_hour) + '</td><td>' + courtStatus(court.is_active) + '</td><td class="table-actions">' + actions + '</td></tr>';
      }).join("");
      content = '<div class="table-wrap"><table class="table"><thead><tr><th>Court</th><th>Venue</th><th>Sport</th><th>Price per hour</th><th>Status</th><th>Actions</th></tr></thead><tbody>' + (courtRows || '<tr><td colspan="6" class="text-secondary">No courts are available in this data source.</td></tr>') + '</tbody></table></div>';
    }
    var stateText = dataMode === "demo" ? "Demo data" : (authUser && authUser.role === "ADMIN" ? "Manage the shared catalogue" : "Sports information");
    var modeNotice = editable || (dataMode === "api" && authUser && authUser.role === "ADMIN")
      ? pendingWriteNotice()
      : (dataMode === "demo" ? demoNotice("Court catalogue is fictional in Demo Mode. Admin catalogue is read-only.") : "");
    var registryErrors = ["sports", "venues", "courts"].filter(function (key) { return resources[key].status === "error"; }).map(function (key) { return resourceError(key, resources[key].error); }).join("");
    return heading(active, '<button class="btn btn-outline-secondary" data-court-refresh><i class="bi bi-arrow-clockwise me-1"></i>Refresh</button>') +
      modeNotice + stats("court-registry", [sportCount, venueCount, courtCount, activeVenueCount], dataMode !== "demo") + registryErrors + tabMarkup +
      '<section class="panel-card registry-panel" id="registry-panel" role="tabpanel" aria-labelledby="registry-tab-' + registryTab + '"><div class="panel-head"><div><h2>' + (registryTab === "sports" ? "Sports" : registryTab === "venues" ? "Venues" : "Courts") + '</h2><p>' + stateText + '</p></div></div>' + controls + form + '<div class="registry-content">' + content + '</div><div class="registry-empty alert alert-light" data-registry-empty hidden>No records match these filters.</div></section>';
  }
  function schedulePage(adminView) {
    var resources = currentResources(true);
    var courts = resources.courts;
    var venues = resources.venues;
    var slotsState = dataMode === "demo" ? resources.slots : scheduleState;
    var canManageApi = dataMode === "api" && authUser && (authUser.role === "OWNER" || (adminView && authUser.role === "ADMIN")) && window.CourtApi.hasAccessToken();
    var rows = "";
    var statusBlock = "";
    if (slotsState.status === "loading" || slotsState.status === "idle") statusBlock = '<div class="panel-body">Loading time slots...</div>';
    else if (slotsState.status === "error") statusBlock = '<div class="panel-body">' + resourceError("time slots", slotsState.error) + "</div>";
    else {
      var visibleSlots = slotsState.data.filter(function (slot) {
        var court = courts.data.find(function (item) { return item.id === slot.court_id; });
        var venue = court && venues.data.find(function (item) { return item.id === court.venue_id; });
        var sport = court && resources.sports.data.find(function (item) { return item.id === court.sport_id; });
        return scheduleUtils.matchesScheduleFilters(slot, {
          venueId: court && court.venue_id,
          venueName: venue && venue.name,
          courtName: court && court.name,
          sportName: sport && sport.name
        }, scheduleFilters);
      });
      if (!visibleSlots.length) statusBlock = '<div class="panel-body text-secondary" role="status">' + (slotsState.data.length ? "No time slots match this filter." : "No time slots are available yet. Add one after a Court is configured.") + ' The active flag does not indicate booking availability.</div>';
      else {
        rows = visibleSlots.map(function (slot) {
          var court = courts.data.find(function (item) { return item.id === slot.court_id; });
          var venue = court && venues.data.find(function (item) { return item.id === court.venue_id; });
          var sport = court && resources.sports.data.find(function (item) { return item.id === court.sport_id; });
          var actions = '<div class="table-action-group">' + detailButton("time-slots", slot.id);
          if (dataMode === "demo" || canManageApi) actions += '<div class="crud-actions">' + crudOpenButton("slots", slot.id, "Edit") + crudDeleteButton("slots", slot.id) + "</div>";
          actions += '</div>';
          return '<tr><td>' + apiDate(slot.slot_date) + '</td><td>' + esc(venue ? venue.name : (court ? "Venue #" + court.venue_id : "Court #" + slot.court_id)) + '</td><td>' + esc(court ? court.name : "Court #" + slot.court_id) + '</td><td>' + esc(sport ? sport.name : "?") + '</td><td>' + apiTime(slot.start_time) + ' - ' + apiTime(slot.end_time) + '</td><td>' + courtStatus(slot.is_active) + '</td><td class="table-actions">' + actions + '</td></tr>';
        }).join("");
        statusBlock = '<div class="table-wrap"><table class="table"><thead><tr><th>Date</th><th>Venue</th><th>Court</th><th>Sport</th><th>Time</th><th>Status</th><th>Actions</th></tr></thead><tbody>' + rows + '</tbody></table></div><div class="table-foot">Active status describes the schedule entry, not booking availability.</div>';
      }
    }
    var courtOptions = courts.data.map(function (court) {
      var venue = venues.data.find(function (item) { return item.id === court.venue_id; });
      return '<option value="' + esc(court.id) + '" ' + (String(court.id) === String(scheduleFilters.courtId) ? "selected" : "") + '>' + esc((venue ? venue.name + " - " : "") + court.name) + '</option>';
    }).join("");
    var venueOptions = venues.data.map(function (venue) {
      return '<option value="' + esc(venue.id) + '" ' + (String(venue.id) === String(scheduleFilters.venueId) ? "selected" : "") + '>' + esc(venue.name) + '</option>';
    }).join("");
    var activeSlots = resources.slots.status === "loaded" ? resources.slots.data.filter(function (slot) { return slot.is_active; }).length : "?";
    var relationErrors = ["venues", "courts", "sports"].filter(function (key) { return resources[key].status === "error"; }).map(function (key) { return resourceError(key, resources[key].error); }).join("");
    var refreshing = dataMode !== "demo" && slotsState.status === "loading";
    var scheduleActions = '<div class="page-heading-actions schedule-heading-actions"><button class="btn btn-outline-secondary" type="button" data-schedule-retry ' + (refreshing ? 'disabled aria-busy="true"' : '') + '><i class="bi bi-arrow-clockwise me-1"></i>' + (refreshing ? "Loading..." : "Refresh") + '</button>' +
      ((dataMode === "demo" || canManageApi) ? crudOpenButton("slots", null, "Add time slot", "btn-success") : "") + '</div>';
    return relationErrors + heading(adminView ? "admin-schedule" : "schedule", scheduleActions) + pendingWriteNotice() +
      stats("court-overview", [resources.sports.status === "loaded" ? resources.sports.data.length : "?", venues.status === "loaded" ? venues.data.length : "?", courts.status === "loaded" ? courts.data.length : "?", activeSlots], true) +
      '<p class="small text-secondary mt-2">Times follow the venue schedule?s local clock.</p>' +
      panel(adminView ? "Time slots" : "Court schedule",
        '<div class="toolbar schedule-toolbar"><input class="form-control schedule-search" type="search" data-schedule-search data-focus-key="schedule-search" value="' + esc(scheduleFilters.search) + '" placeholder="Search venue, court, sport, time, or date (e.g. 23/10)" aria-label="Search schedule details or a date">' +
        calendarPickerMarkup("schedule-filter", "Filter date", scheduleFilters.date) +
        '<select class="form-select" data-schedule-venue data-focus-key="schedule-venue" aria-label="Filter by venue"><option value="">All venues</option>' + venueOptions + '</select>' +
        '<select class="form-select" data-schedule-court data-focus-key="schedule-court" aria-label="Filter by court"><option value="">All courts</option>' + courtOptions + '</select>' +
        '<select class="form-select" data-schedule-status data-focus-key="schedule-status" aria-label="Filter by status"><option value="">All statuses</option><option value="true" ' + (scheduleFilters.status === "true" ? "selected" : "") + '>Active</option><option value="false" ' + (scheduleFilters.status === "false" ? "selected" : "") + '>Inactive</option></select>' +
        '<button class="btn btn-outline-secondary" type="button" data-schedule-reset>Reset filters</button></div>' +
        ((dataMode === "demo" || canManageApi) ? crudFormMarkup("slots", resources) : "") + statusBlock,
        dataMode === "demo" ? "Demo refresh restores the sample Time Slots." : "Active status describes the schedule entry, not booking availability.",
        "", "calendar-panel-card");
  }
  function checkinPage(active, admin) {
    if (admin) {
      if (dataMode !== "demo") {
        var filters = '<div class="toolbar admin-filter-toolbar"><input class="form-control" type="search" data-admin-checkin-booking value="' + esc(adminCheckinsFilters.booking_id) + '" placeholder="Booking ID" aria-label="Filter booking ID">' + [["venue_id", "Venue ID"], ["court_id", "Court ID"], ["checked_in_by", "Owner ID"]].map(function (field) { return '<input class="form-control" type="number" min="1" data-admin-checkin-field="' + field[0] + '" value="' + esc(adminCheckinsFilters[field[0]]) + '" placeholder="' + field[1] + '" aria-label="Filter ' + field[1] + '">'; }).join("") + calendarPickerMarkup("admin-checkins-from", "Date from", adminCheckinsFilters.date_from, { filterAttribute: ' data-admin-date-filter="checkins" data-admin-date-field="date_from"' }) + calendarPickerMarkup("admin-checkins-to", "Date to", adminCheckinsFilters.date_to, { filterAttribute: ' data-admin-date-filter="checkins" data-admin-date-field="date_to"' }) + '<button class="btn btn-outline-secondary" type="button" data-admin-filter-clear="checkins">Clear filters</button></div>';
        var content = adminListState(adminCheckinsState);
        if (adminCheckinsState.status === "loaded" && adminCheckinsState.data.items.length) {
          var rows = adminCheckinsState.data.items.map(function (item) {
            return '<tr><td class="table-primary-text">' + esc(item.id) + '</td><td>' + esc(item.venue_id) + '</td><td>' + esc(item.court_id) + '</td><td>' + esc(item.checked_in_by || "—") + '</td><td>' + esc(item.checked_in_at || "—") + '</td><td>' + statusBadge(item.status) + '</td><td>' + esc(item.user_id) + '</td><td class="table-actions"><button class="btn btn-sm btn-outline-secondary" type="button" data-admin-booking-detail="' + esc(item.id) + '">Booking details</button></td></tr>';
          }).join("");
          content = '<div class="table-wrap"><table class="table"><thead><tr><th>Booking</th><th>Venue</th><th>Court</th><th>Checked in by</th><th>Check-in time</th><th>Status</th><th>User</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>' + adminPagination("checkins", adminCheckinsState.data);
        }
        return heading(active) + panel("Check-ins", filters + content, "History recorded on bookings · read-only");
      }
      var adminRows = data.checkins;
      return heading(active) + demoNotice("Sample check-ins are shown for preview only.") + panel("Recent check-ins", '<div class="toolbar admin-filter-toolbar" data-filter-toolbar><input class="form-control" type="search" data-table-search data-admin-search placeholder="Search check-in, booking or customer" aria-label="Search check-ins"><select class="form-select" data-status-filter aria-label="Filter check-in status"><option value="">All statuses</option><option>Verified</option><option>Manual</option></select><button class="btn btn-outline-secondary" type="button" data-filter-reset>Reset filters</button></div>' + table(["Check-in ID", "Booking", "Customer", "Venue / court", "Check-in time", "Status"], adminRows) + '<div class="table-foot" data-filter-count>Showing ' + adminRows.length + ' records</div>', "Demo records only");
    }
    var demo = dataMode === "demo";
    var statusLabel = { idle: "IDLE", loading: "STARTING", scanning: "SCANNING", stopping: "STOPPING", success: "SUCCESS", error: "ERROR" }[scannerState] || "IDLE";
    var cameraFrameClass = ["idle", "success", "error"].indexOf(scannerState) >= 0 && !scannerInstance ? "qr-camera-frame--idle" : "qr-camera-frame--active";
    var result = scanResult ? '<div class="alert ' + (scanResult.ok ? "alert-success" : "alert-danger") + '" role="status"><strong>' + esc(scanResult.title) + '</strong><p class="mb-1 mt-2">' + esc(scanResult.message) + '</p>' + scanResultBookingMarkup() + '</div>' : '<p class="text-secondary small" data-scan-result>No QR result yet.</p>';
    var scannerBusy = scannerStarting || ["loading", "scanning", "stopping"].indexOf(scannerState) >= 0;
    var controls = '<div class="qr-camera-controls"><button class="btn btn-success" data-scanner-start ' + (scannerBusy || ownerCheckinPending ? "disabled" : "") + '>Start Camera</button><button class="btn btn-outline-secondary" data-scanner-stop ' + (scannerState === "stopping" || (!scannerInstance && !qrScanner && !scannerStarting) ? "disabled" : "") + '>Stop Camera</button></div>';
    var cameraPanel = '<div class="scanner-frame qr-camera-frame ' + cameraFrameClass + '"><div id="qr-reader" aria-label="Camera preview"></div>' + (scannerState === "idle" ? '<div class="qr-camera-placeholder"><i class="bi bi-qr-code-scan"></i><strong>Camera preview</strong><small>Start the camera when you are ready to scan.</small></div>' : "") + '</div><div class="qr-scanner-footer"><div class="qr-scanner-toolbar"><div class="qr-scanner-status qr-scanner-status--' + scannerState + '" role="status" data-scanner-status>' + statusLabel + '</div>' + controls + '</div><div class="qr-scanner-result" data-scanner-result-host>' + result + '</div></div>';
    var notice = demo ? demoNotice("Demo Only: scan one of the QR tokens from this page or enter it manually below. No real booking token is shown or accepted.") : '<div class="alert alert-info py-2 small" role="status">Scan a booking QR code or enter its code to check in.</div>';
    var manual = demo ? '<div class="panel-body"><label class="form-label" for="demo-qr-token">Demo QR token input</label><div class="input-group"><input class="form-control" id="demo-qr-token" autocomplete="off" placeholder="Enter a Demo Only QR token"><button class="btn btn-outline-secondary" data-demo-qr-submit>Check token</button></div><small class="text-secondary">Manual input is for Demo Mode testing only.</small></div>' : '<div class="panel-body"><label class="form-label" for="owner-qr-token">QR token</label><div class="input-group"><input class="form-control" id="owner-qr-token" autocomplete="off" placeholder="Scan a booking QR or enter its token"><button class="btn btn-outline-primary" type="button" data-owner-qr-submit>Check in</button></div><small class="text-secondary">Your code stays private and is not shown in the result.</small></div>';
    var examples = demo ? '<div class="panel-body"><p class="small text-secondary mb-2">Demo Only test tokens</p><div class="qr-demo-token-list">' + demoBookings.map(function (booking) { return '<div class="qr-demo-token"><span><small>' + esc(booking.status) + '</small><br><code>' + esc(booking.qr_token) + '</code></span><button class="btn btn-sm btn-outline-secondary" type="button" data-copy-qr="' + esc(booking.qr_token) + '">Copy</button></div>'; }).join("") + '<div class="qr-demo-token"><span><small>INVALID</small><br><code>demo-qr-invalid</code></span><button class="btn btn-sm btn-outline-secondary" type="button" data-copy-qr="demo-qr-invalid">Copy</button></div></div></div>' : '<div class="panel-body text-secondary">Use a booking QR code or enter its code to check in.</div>';
    return heading(active) + notice + '<div class="scanner-layout mb-3">' + panel("QR Check-in", cameraPanel, "Camera access starts only after you press Start Camera") + panel("Check-in result", manual + examples, demo ? "Demo Only" : "Booking check-in") + '</div>';
  }
  function checkDemoQr(token) {
    if (dataMode !== "demo") {
      setScanResult(false, "Not available", "Live check-in is not available here. No request was sent.");
      return;
    }
    var booking = demoBookings.find(function (item) { return item.qr_token === token; });
    if (!booking) { setScanResult(false, "Invalid QR", "This token does not match a Demo booking."); return; }
    if (booking.owner_id !== "demo-owner") { setScanResult(false, "Access Denied", "This Demo booking belongs to another Owner.", booking); return; }
    if (booking.status === "CHECKED_IN") { setScanResult(false, "Already Checked In", "This booking has already been checked in.", booking); return; }
    if (booking.status === "COMPLETED") { setScanResult(false, "Booking Already Completed", "Completed bookings cannot be checked in.", booking); return; }
    if (booking.status === "CANCELLED") { setScanResult(false, "Booking Cancelled", "Cancelled bookings cannot be checked in.", booking); return; }
    if (booking.status === "EXPIRED") { setScanResult(false, "Booking Expired", "Expired bookings cannot be checked in.", booking); return; }
    if (booking.status !== "CONFIRMED") { setScanResult(false, "Booking Not Ready", "Only CONFIRMED bookings can be checked in.", booking); return; }
    booking.status = "CHECKED_IN";
    booking.checkin_status = "CHECKED_IN";
    setScanResult(true, "Check-in Successful", "Booking was checked in in Demo Mode.", booking);
  }
  function setScanResult(ok, title, message, booking) {
    scanResult = { ok: ok, title: title, message: message, booking: booking || null };
    updateScannerResult();
    updateScannerState();
  }
  function scanResultBookingMarkup() {
    if (!scanResult || !scanResult.booking) return "";
    if (dataMode === "demo") {
      var demoBooking = scanResult.booking;
      return '<div class="small">' + esc(demoBooking.id + " | " + demoBooking.court + " | " + demoBooking.date + " " + demoBooking.start_time + " - " + demoBooking.end_time) + '</div>';
    }
    var apiBooking = scanResult.booking;
    return '<div class="small">Booking #' + esc(apiBooking.id) + ' · ' + esc(apiBooking.status) + (apiBooking.checked_in_at ? ' · ' + esc(apiBooking.checked_in_at) : '') + '</div>';
  }
  function ownerCheckinErrorMessage(error) {
    var status = error && error.status;
    if (status === 401) return "Your session is missing or expired. Sign in again.";
    if (status === 403) return "This account does not have Owner permission to check in bookings.";
    if (status === 404) return "QR token is invalid, booking was not found, or it is outside your Owner access.";
    if (status === 409) return "This booking was already checked in or is not ready for check-in.";
    if (status === 422) return "The QR token is invalid. Check the token and try again.";
    if (status === 503) return "Check-in service is temporarily unavailable.";
    if (status === 504) return "Check-in service timed out. Try again.";
    if (status === 0) return "Could not connect. Try again in a moment.";
    return "Could not check in this booking. Try again.";
  }
  function submitOwnerCheckin(qrToken, fromScanner) {
    if (dataMode === "demo") {
      checkDemoQr(qrToken);
      if (scanResult && scanResult.ok && (qrScanner || scannerInstance)) return stopQrScanner();
      return Promise.resolve();
    }
    if (ownerCheckinPending) return Promise.resolve();
    if (fromScanner && (scannerState !== "scanning" || scannerStopPromise || !qrScanner)) return Promise.resolve();
    if (!String(qrToken || "").trim()) {
      setScanResult(false, "QR token required", "Scan a booking QR or enter its token first.");
      return Promise.resolve();
    }
    ownerCheckinPending = true;
    var submit = document.querySelector("[data-owner-qr-submit]");
    if (submit) { submit.disabled = true; submit.textContent = "Checking..."; }
    var succeeded = false;
    updateScannerState();
    return window.OwnerCheckinApi.checkIn(qrToken).then(function (result) {
      succeeded = true;
      setScanResult(true, "Check-in successful", "The booking was checked in.", {
        id: result && result.booking_id,
        status: result && result.status || "CHECKED_IN",
        checked_in_at: result && result.checked_in_at
      });
      ownerBookingsState.status = "idle";
    }).catch(function (error) {
      setScanResult(false, "Check-in failed", ownerCheckinErrorMessage(error));
    }).finally(function () {
      ownerCheckinPending = false;
      var input = document.getElementById("owner-qr-token");
      var button = document.querySelector("[data-owner-qr-submit]");
      if (input) input.disabled = false;
      if (button) { button.disabled = false; button.textContent = "Check in"; }
      updateScannerState();
    }).then(function () {
      if (succeeded && (qrScanner || scannerInstance)) return stopQrScanner();
    });
  }
  function updateScannerResult() {
    var host = document.querySelector("[data-scanner-result-host]");
    if (!host) return;
    if (!scanResult) { host.innerHTML = '<p class="text-secondary small" data-scan-result>No QR result yet.</p>'; return; }
    host.innerHTML = '<div class="alert ' + (scanResult.ok ? "alert-success" : "alert-danger") + '" role="status"><strong>' + esc(scanResult.title) + '</strong><p class="mb-1 mt-2">' + esc(scanResult.message) + '</p>' + scanResultBookingMarkup() + '</div>';
  }
  function updateScannerState(label) {
    var status = document.querySelector("[data-scanner-status]");
    if (status) {
      status.textContent = label || scannerState.toUpperCase();
      status.className = "qr-scanner-status qr-scanner-status--" + scannerState;
    }
    var start = document.querySelector("[data-scanner-start]");
    var stop = document.querySelector("[data-scanner-stop]");
    if (start) start.disabled = scannerStarting || ownerCheckinPending || ["loading", "scanning", "stopping"].indexOf(scannerState) >= 0 || !!scannerInstance || !!qrScanner;
    if (stop) stop.disabled = scannerState === "stopping" || (!scannerInstance && !qrScanner && !scannerStarting);
    var placeholder = document.querySelector(".qr-camera-placeholder");
    if (placeholder) placeholder.hidden = ["loading", "scanning", "stopping"].indexOf(scannerState) >= 0;
    var frame = document.querySelector(".qr-camera-frame");
    if (frame) {
      var idleFrame = ["idle", "success", "error"].indexOf(scannerState) >= 0 && !scannerInstance;
      frame.classList.toggle("qr-camera-frame--idle", idleFrame);
      frame.classList.toggle("qr-camera-frame--active", !idleFrame);
    }
  }
  function scannerErrorMessage(error) {
    var name = error && error.name || "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") return "Camera permission was denied. Allow camera access in your browser settings, then try again.";
    if (name === "NotFoundError" || name === "DevicesNotFoundError") return "No camera was found. Connect or enable a webcam, then try again.";
    if (name === "NotReadableError" || name === "TrackStartError" || name === "AbortError") return "The camera is busy or could not start. Close other apps using it, then try again.";
    if (location.protocol !== "https:" && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") return "Camera access requires HTTPS or localhost.";
    return error && error.message ? error.message : "Could not start the camera. Check camera permission and try again.";
  }
  function releaseQrVideoTracks() {
    document.querySelectorAll("#qr-reader video").forEach(function (video) {
      var stream = video.srcObject;
      if (!stream || typeof stream.getTracks !== "function") return;
      stream.getTracks().forEach(function (track) { track.stop(); });
      video.srcObject = null;
    });
  }
  function startQrScanner() {
    if (scannerStarting || scannerStopPromise || ownerCheckinPending || ["loading", "scanning", "stopping"].indexOf(scannerState) >= 0) return;
    if (qrScanner || scannerInstance) {
      stopQrScanner().then(function (stopped) {
        if (stopped && currentRoute() === "qr-checkin") startQrScanner();
      });
      return;
    }
    if (!window.Html5Qrcode) { scannerState = "error"; scanResult = { ok: false, title: "Scanner library unavailable", message: window.Html5QrcodeLoadError || "html5-qrcode is still loading or could not be loaded. Reload the page and check the local Management Web files.", booking: null }; updateScannerState("ERROR"); updateScannerResult(); return; }
    scannerScanGate.reset();
    scannerStarting = true; scannerState = "loading"; scanResult = null; updateScannerState("STARTING - requesting camera permission"); updateScannerResult();
    var epoch = ++scannerEpoch;
    var activeScanner;
    try {
      activeScanner = new window.Html5Qrcode("qr-reader");
      scannerInstance = activeScanner;
    } catch (error) {
      scannerInstance = null; scannerStarting = false; scannerState = "error"; scanResult = { ok: false, title: "Scanner error", message: scannerErrorMessage(error), booking: null }; updateScannerState("ERROR"); updateScannerResult(); return;
    }
    scannerStartPromise = Promise.resolve().then(function () {
      if (scannerInstance !== activeScanner || epoch !== scannerEpoch) throw new Error("Camera start was cancelled.");
      return Promise.resolve().then(function () { return window.Html5Qrcode.getCameras(); }).then(function (devices) {
        if (scannerInstance !== activeScanner || epoch !== scannerEpoch) throw new Error("Camera start was cancelled.");
        if (!devices || !devices.length) { var missing = new Error("No camera was found. Connect or enable a webcam, then try again."); missing.name = "NotFoundError"; throw missing; }
        var selected = devices.find(function (device) { return /webcam|integrated|front|camera/i.test(device.label || ""); }) || devices[0];
        return activeScanner.start(selected.id, { fps: 10, qrbox: { width: 240, height: 240 }, aspectRatio: 4 / 3 }, function (decodedText) {
          var qrToken = String(decodedText || "").trim();
          if (epoch !== scannerEpoch || scannerInstance !== activeScanner || qrScanner !== activeScanner || scannerStopPromise || scannerState !== "scanning" || !scannerScanGate.tryBegin(qrToken)) return;
          submitOwnerCheckin(qrToken, true).then(function () { scannerScanGate.finish(); }, function () { scannerScanGate.finish(); });
        }, function () {});
      });
    }).then(function () {
      if (scannerInstance !== activeScanner || epoch !== scannerEpoch) return;
      qrScanner = activeScanner; scannerStarting = false; scannerState = "scanning"; updateScannerState("SCANNING");
    }).catch(function (error) {
      if (scannerInstance !== activeScanner || epoch !== scannerEpoch) return;
      if (error && error.message === "Camera start was cancelled.") { scannerState = "idle"; updateScannerState("IDLE"); return; }
      var message = scannerErrorMessage(error);
      var cleanup = Promise.resolve();
      if (activeScanner.isScanning || activeScanner.stateManager && activeScanner.stateManager.getState && activeScanner.stateManager.getState() === 2) {
        cleanup = Promise.resolve().then(function () { return activeScanner.stop(); });
      }
      return cleanup.then(function () {
        if (activeScanner.isScanning || activeScanner.stateManager && activeScanner.stateManager.getState && activeScanner.stateManager.getState() === 2) throw new Error("Scanner is still active.");
        releaseQrVideoTracks();
        return typeof activeScanner.clear === "function" ? activeScanner.clear() : undefined;
      }).then(function () {
        if (scannerInstance === activeScanner) scannerInstance = null;
        if (qrScanner === activeScanner) qrScanner = null;
        scannerStarting = false; scannerState = "error"; scanResult = { ok: false, title: "Camera error", message: message, booking: null }; updateScannerState("ERROR"); updateScannerResult();
      }).catch(function (cleanupError) {
        scannerStarting = false; scannerState = "error"; scanResult = { ok: false, title: "Camera cleanup error", message: message + " Camera cleanup failed: " + (cleanupError && cleanupError.message ? cleanupError.message : "unknown error") + ". Press Stop Camera to retry cleanup.", booking: null }; updateScannerState("ERROR"); updateScannerResult();
      });
    }).finally(function () { scannerStartPromise = null; updateScannerState(); });
  }
  function stopQrScanner() {
    if (scannerStopPromise) return scannerStopPromise;
    var current = qrScanner || scannerInstance;
    ++scannerEpoch;
    scannerScanGate.reset();
    if (!current) { scannerStarting = false; scannerState = "idle"; updateScannerState("IDLE"); return Promise.resolve(true); }
    scannerState = "stopping"; updateScannerState("STOPPING");
    scannerStopPromise = Promise.resolve().then(function () {
      return scannerStartPromise ? scannerStartPromise.then(function () { return true; }, function () { return false; }) : true;
    }).then(function (started) {
      if (!started) throw new Error("Scanner did not finish starting; camera cleanup must be retried.");
      if (current.isScanning || current.stateManager && current.stateManager.getState && current.stateManager.getState() === 2) return Promise.resolve(current.stop()).then(function () { return true; });
      return true;
    }).then(function (started) {
      if (!started) return false;
      if (current.isScanning || current.stateManager && current.stateManager.getState && current.stateManager.getState() === 2) throw new Error("Scanner did not stop; camera cleanup was not attempted.");
      releaseQrVideoTracks();
      return typeof current.clear === "function" ? current.clear() : undefined;
    }).then(function () {
      scannerInstance = null; qrScanner = null; scannerStarting = false; scannerState = "idle"; updateScannerState("IDLE"); return true;
    }).catch(function (error) {
      scannerState = "error"; scanResult = { ok: false, title: "Camera stop error", message: error && error.message ? error.message : "Could not stop the camera safely. Retry Stop Camera.", booking: null }; updateScannerState("ERROR"); updateScannerResult(); return false;
    }).finally(function () { scannerStopPromise = null; updateScannerState(); });
    return scannerStopPromise;
  }
  function revenuePage() {
    if (dataMode !== "demo") {
      return heading("revenue") + panel("Revenue overview", '<div class="panel-body"><p class="mb-0 text-secondary">Revenue information is not available yet.</p></div>', "Revenue summary");
    }
    var values = [42, 61, 52, 72, 66, 84, 76, 95, 73, 87, 67, 100];
    var months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"];
    var bars = values.map(function (height, i) {
      return '<div class="bar-column"><div class="bar ' + (i === 11 ? "current" : "") + '" style="height:' + height + '%"></div><span>' + months[i] + "</span></div>";
    }).join("");
    var chart = '<div class="panel-body"><p class="eyebrow mb-2">Gross revenue · This year</p><p class="revenue-total">₫12,450,000</p><p class="text-secondary mb-2" style="font-size:10px"><span class="trend-up"><i class="bi bi-arrow-up-right"></i> 12.8%</span> compared with last month</p><div class="bar-chart">' + bars + '</div><div class="chart-legend"><span>Monthly revenue summary</span><span>Sample data · VND</span></div></div>';
    var items = [["Badminton", "₫6,820,000", "55%"], ["Football", "₫3,240,000", "26%"], ["Pickleball", "₫2,390,000", "19%"]];
    var breakdown = '<div class="panel-body quick-list">' + items.map(function (item) {
      return '<div class="quick-item"><span class="quick-icon"><i class="bi bi-trophy"></i></span><span class="flex-grow-1"><strong>' + item[0] + "</strong><small>" + item[2] + " of total revenue</small></span><strong>" + item[1] + "</strong></div>";
    }).join("") + "</div>";
    return heading("revenue", actionButton("Download report", "bi-download", "Sample revenue report downloaded.", true)) + demoNotice("Sample figures are shown for preview only.") +
      stats("revenue", ["₫12.45M", "₫4.68M", "₫7.77M", "₫1.24M"]) + '<div class="content-grid">' +
      panel("Revenue overview", chart, "Monthly performance") + panel("Revenue by sport", breakdown, "This month") +
      '</div><p class="text-secondary mt-3" style="font-size:10px"><i class="bi bi-info-circle me-1"></i>Revenue figures are mock data for this interface preview.</p>';
  }
  function peoplePage() {
    if (dataMode !== "demo") {
      var apiToolbar = '<div class="toolbar admin-filter-toolbar"><input class="form-control" type="search" data-admin-user-q value="' + esc(adminUsersFilters.q) + '" placeholder="Search name or email" aria-label="Search users"><select class="form-select" data-admin-user-role aria-label="Filter role"><option value="">All roles</option>' + ["USER", "OWNER", "ADMIN"].map(function (role) { return '<option value="' + role + '" ' + (adminUsersFilters.role === role ? "selected" : "") + '>' + role + '</option>'; }).join("") + '</select><select class="form-select" data-admin-user-active aria-label="Filter account status"><option value="">All statuses</option><option value="true" ' + (adminUsersFilters.is_active === "true" ? "selected" : "") + '>Active</option><option value="false" ' + (adminUsersFilters.is_active === "false" ? "selected" : "") + '>Inactive</option></select></div>';
      var usersContent = adminListState(adminUsersState);
      if (adminUsersState.status === "loaded" && adminUsersState.data.items.length) {
        var userRows = adminUsersState.data.items.map(function (user) {
          var isSelf = Number(user.id) === Number(authUser.id);
          var statusAction = isSelf ? '<button class="btn btn-sm btn-outline-secondary" disabled title="You cannot change your own account status">Current account</button>' : '<button class="btn btn-sm ' + (user.is_active ? "btn-outline-danger" : "btn-outline-success") + '" type="button" data-admin-user-status data-user-id="' + esc(user.id) + '" data-active="' + String(!!user.is_active) + '">' + (user.is_active ? "Deactivate" : "Activate") + '</button>';
          return '<tr><td>' + esc(user.id) + '</td><td class="table-primary-text">' + esc(user.full_name) + '</td><td>' + esc(user.email) + '</td><td>' + esc(user.role) + '</td><td>' + (user.is_active ? badge("Active") : badge("Inactive")) + '</td><td>' + esc(user.created_at || "—") + '</td><td class="table-actions"><div class="table-action-group"><button class="btn btn-sm btn-outline-secondary" type="button" data-admin-user-detail="' + esc(user.id) + '">Details</button>' + statusAction + '</div></td></tr>';
        }).join("");
        usersContent = '<div class="table-wrap"><table class="table"><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>' + userRows + '</tbody></table></div>' + adminPagination("users", adminUsersState.data);
      }
      return heading("people") + panel("Users & Owners", apiToolbar + usersContent, "Account directory · API data");
    }
    var rows = data.people.map(function (row) {
      var accountId = row[0] || "";
      return '<tr data-account-row data-role="' + esc(row[3]) + '" data-status="' + esc(row[5]) + '"><td class="account-id">' + esc(accountId || "ID unavailable") + '</td><td class="table-primary-text">' + esc(row[1]) + '</td><td>' + esc(row[2]) + '</td><td>' + esc(row[3]) + '</td><td>' + esc(row[4]) + '</td><td>' + badge(row[5]) + '</td><td class="table-actions"><div class="table-action-group"><button class="btn btn-sm btn-outline-secondary" type="button" data-account-detail="' + esc(accountId) + '">Details</button></div></td></tr>';
    }).join("");
    var accountStats = demoAccountStats();
    return heading("people") + demoNotice("Sample accounts are shown for preview only. Changes are not saved.") +
      stats("people", accountStats) +
      panel("Account directory", '<div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-table-search type="search" placeholder="Search name, email or ID" aria-label="Search accounts"></div><select class="form-select" data-account-role><option value="">All roles</option><option>User</option><option>Court Owner</option></select><select class="form-select" data-account-status><option value="">All statuses</option><option>Active</option><option>Pending</option><option>Inactive</option></select></div>' +
      '<div class="table-wrap"><table class="table"><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th>Status</th><th>Actions</th></tr></thead><tbody id="admin-account-rows">' + rows + '</tbody></table></div><div class="table-foot"><span data-account-count>Showing ' + data.people.length + ' of ' + data.people.length + ' Demo accounts</span></div>', "Demo records only");
  }
  function profilePage(active, admin) {
    if (authUser) {
      var accountRows = [["Account ID", authUser.id], ["Full name", authUser.full_name], ["Email", authUser.email], ["Phone", authUser.phone], ["Role", authUser.role], ["Status", authUser.is_active ? "Active" : "Inactive"]].filter(function (row) { return row[1] !== null && row[1] !== undefined && row[1] !== ""; });
      var details = '<div class="panel-body">' + accountRows.map(function (row) { return '<div class="detail-row"><span>' + esc(row[0]) + '</span><strong>' + esc(row[1]) + '</strong></div>'; }).join("") + '</div>';
      return heading(active) + '<div class="alert alert-info" role="status">Profile details are available in read-only mode.</div>' + panel("Account information", details, "Your profile");
    }
    var name = admin ? "Admin User" : "Nguyễn Văn A";
    var email = admin ? "admin@sportbooking.vn" : "owner@sportbooking.vn";
    return heading(active) + demoNotice("Sample profile information is shown for preview only.") + '<div class="profile-layout"><section class="profile-card profile-summary"><span class="avatar">' + (admin ? "AU" : "NA") +
      "</span><h2>" + name + "</h2><p>" + (admin ? "System Administrator" : "Court Owner") + " · Member since 2025</p>" + badge("Active") +
      '<div class="profile-divider"></div><div class="detail-row"><span>Account ID</span><strong>' + (admin ? "ADM-0001" : "OWN-0108") +
      '</strong></div><div class="detail-row"><span>Role</span><strong>' + (admin ? "Administrator" : "Court Owner") + '</strong></div></section>' +
      '<section class="profile-card"><div class="d-flex justify-content-between align-items-start mb-3"><div><h2 class="h6 fw-bold mb-1">Personal information</h2><p class="text-secondary mb-0" style="font-size:10px">Update your profile details and contact information.</p></div><i class="bi bi-person-vcard text-success fs-5"></i></div>' +
      '<form id="profile-form" class="row g-3"><div class="col-md-6"><label class="form-label">Full name</label><input class="form-control" value="' + name +
      '"></div><div class="col-md-6"><label class="form-label">Email address</label><input class="form-control" type="email" value="' + email +
      '"></div><div class="col-md-6"><label class="form-label">Phone number</label><input class="form-control" value="+84 912 345 678"></div><div class="col-md-6"><label class="form-label">Account role</label><input class="form-control" value="' +
      (admin ? "Administrator" : "Court Owner") + '" disabled></div><div class="col-12"><label class="form-label">Address</label><input class="form-control" value="Cầu Giấy, Hà Nội"></div><div class="col-12 d-flex justify-content-end"><button class="btn btn-success" type="submit"><i class="bi bi-check2 me-1"></i>Save changes</button></div></form></section></div>';
  }
  function pageFor(active) {
    if (active === "dashboard" || active === "admin-dashboard") return dashboard(active);
    if (active === "venues" || active === "admin-venues") return venuePage(active, active === "admin-venues");
    if (active === "schedule" || active === "admin-schedule") return schedulePage(active === "admin-schedule");
    if (active === "owner-bookings") return bookingPage(active, false);
    if (active === "admin-bookings") return bookingPage(active, true);
    if (active === "qr-checkin") return checkinPage(active, false);
    if (active === "checkins") return checkinPage(active, true);
    if (active === "revenue") return revenuePage();
    if (active === "people") return peoplePage();
    if (active === "owner-profile") return profilePage(active, false);
    if (active === "admin-profile") return profilePage(active, true);
    return dashboard("dashboard");
  }
  function toast(message) {
    var host = document.getElementById("toast-area");
    var node = document.createElement("div");
    if (!host) {
      host = document.createElement("div");
      host.id = "toast-area";
      document.body.appendChild(host);
    }
    if (!window.bootstrap || !window.bootstrap.Toast) {
      node.className = "alert alert-info";
      node.setAttribute("role", "status");
      node.textContent = message;
      host.appendChild(node);
      window.setTimeout(function () { node.remove(); }, 2600);
      return;
    }
    node.className = "toast align-items-center border-0";
    node.setAttribute("role", "status");
    node.innerHTML = '<div class="d-flex"><div class="toast-body"><i class="bi bi-info-circle text-success me-2"></i>' + esc(message) + '</div><button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>';
    host.appendChild(node);
    var instance = new window.bootstrap.Toast(node, { delay: 2600 });
    node.addEventListener("hidden.bs.toast", function () { node.remove(); });
    instance.show();
  }
  function filterRows() {
    var search = (document.querySelector("[data-table-search]") || {}).value || "";
    var status = (document.querySelector("[data-status-filter]") || {}).value || "";
    var accountRole = (document.querySelector("[data-account-role]") || {}).value || "";
    var accountStatus = (document.querySelector("[data-account-status]") || {}).value || "";
    var visibleAccounts = 0;
    document.querySelectorAll(".table tbody tr").forEach(function (row) {
      var matches = row.innerText.toLowerCase().indexOf(search.toLowerCase()) >= 0 &&
        (!status || row.innerText.toLowerCase().indexOf(status.toLowerCase()) >= 0) &&
        (!row.hasAttribute("data-account-row") || ((!accountRole || row.dataset.role === accountRole) && (!accountStatus || row.dataset.status === accountStatus)));
      row.hidden = !matches;
      if (matches && row.hasAttribute("data-account-row")) visibleAccounts += 1;
    });
    var count = document.querySelector("[data-account-count]");
    if (count) count.textContent = "Showing " + visibleAccounts + " of " + data.people.length + " Demo accounts";
    var filteredCount = document.querySelector("[data-filter-count]");
    if (filteredCount) {
      var visibleRows = Array.prototype.filter.call(document.querySelectorAll(".table tbody tr"), function (row) { return !row.hidden; }).length;
      filteredCount.textContent = "Showing " + visibleRows + " records";
    }
  }
  function applyRegistryFilters() {
    var searchInput = document.querySelector("[data-registry-search]");
    var query = (searchInput && searchInput.value || "").trim().toLowerCase();
    if (registryTab === "sports") sportSearch = searchInput ? searchInput.value : sportSearch;
    if (registryTab === "venues") venueSearch = searchInput ? searchInput.value : venueSearch;
    if (registryTab === "courts") courtSearch = searchInput ? searchInput.value : courtSearch;
    var sportFilter = document.querySelector("[data-registry-sport-filter]");
    var activeFilter = document.querySelector("[data-registry-active-filter], [data-registry-status]");
    var venueFilter = document.querySelector("[data-registry-venue-filter]");
    if (sportFilter) registryFilters.sportId = sportFilter.value;
    if (activeFilter) registryFilters.active = activeFilter.value;
    if (venueFilter) registryFilters.venueId = venueFilter.value;
    var visible = 0;
    var rows = document.querySelectorAll("[data-registry-row]");
    rows.forEach(function (row) {
      var show = row.dataset.search.indexOf(query) >= 0;
      if (registryTab === "sports" || registryTab === "venues") show = show && (!registryFilters.active || row.dataset.active === registryFilters.active);
      if (registryTab === "venues") show = show && (!registryFilters.sportId || row.dataset.sportIds.indexOf("|" + registryFilters.sportId + "|") >= 0);
      if (registryTab === "courts") show = show && (!registryFilters.sportId || row.dataset.sportId === registryFilters.sportId) &&
        (!registryFilters.active || row.dataset.active === registryFilters.active) &&
        (!registryFilters.venueId || row.dataset.venueId === registryFilters.venueId);
      row.hidden = !show;
      if (show) visible += 1;
    });
    var empty = document.querySelector("[data-registry-empty]");
    if (empty) empty.hidden = visible > 0 || rows.length === 0;
  }
  function saveDemoRecord(form) {
    var resource = form.dataset.crudResource;
    var id = form.dataset.crudId || null;
    var values = demoFormValues(form, resource);
    var error = validateDemoForm(resource, values, id);
    if (error) {
      form.querySelectorAll(".field-error").forEach(function (node) { node.textContent = ""; });
      form.querySelectorAll(".is-invalid").forEach(function (node) { node.classList.remove("is-invalid"); });
      var field = error.field === "slot_date" ? form.querySelector('[data-calendar-id="slot-date"] [data-calendar-toggle]') : form.elements.namedItem(error.field);
      var feedback = form.querySelector('[data-field-error="' + error.field + '"]');
      if (field) { field.classList.add("is-invalid"); if (error.field === "slot_date") field.setAttribute("aria-invalid", "true"); }
      if (feedback) feedback.textContent = error.message;
      if (field) field.focus();
      return;
    }
    var records = recordsFor(resource);
    var existing = id ? records.find(function (item) { return String(item.id) === String(id); }) : null;
    if (resource === "slots") delete values.venue_id;
    if (existing) Object.assign(existing, values);
    else {
      values.id = nextDemoId(records);
      records.push(values);
    }
    crudFormState = null;
    render();
    toast((existing ? "Updated " : "Added ") + ({ sports: "sport", venues: "venue", courts: "court", slots: "time slot" }[resource]) + " in Demo Mode.");
  }
  function apiFormValues(form, resource) {
    var values = Object.fromEntries(new FormData(form).entries());
    values.is_active = form.elements.is_active.checked;
    if (resource === "sports") {
      values.description = values.description || null;
    } else if (resource === "venues") {
      values.owner_id = Number(authUser.role === "ADMIN" ? values.owner_id : authUser.id);
      values.description = values.description || null;
      values.phone = values.phone || null;
    } else if (resource === "courts") {
      values.venue_id = Number(values.venue_id);
      values.sport_id = Number(values.sport_id);
      values.description = values.description || null;
    } else if (resource === "slots") {
      values.venue_id = Number(values.venue_id);
      values.court_id = Number(values.court_id);
      var venueCourts = scheduleUtils.courtsForVenue(courtResources.courts.data, values.venue_id);
      if (!venueCourts.some(function (item) { return String(item.id) === String(values.court_id); })) return { error: "Choose a court that belongs to the selected venue." };
      var date = scheduleUtils.parseDateInput(values.slot_date);
      if (!date.valid) return { error: "Enter a valid date as dd/MM/yyyy, for example 23/10/2026." };
      values.slot_date = date.iso;
      delete values.venue_id;
      if (values.start_time && values.start_time.length === 5) values.start_time += ":00";
      if (values.end_time && values.end_time.length === 5) values.end_time += ":00";
      var boundary = /^(?:[01]\d|2[0-3]):(?:00|30):00$/;
      if (!boundary.test(values.start_time) || !boundary.test(values.end_time)) return { error: "Choose start and end times in 30-minute increments." };
      if (values.start_time >= values.end_time) return { error: "Start time must be earlier than end time." };
      var currentSlot = form.dataset.crudId ? courtResources.slots.data.find(function (item) { return String(item.id) === String(form.dataset.crudId); }) : null;
      var futureError = scheduleUtils.validateFutureStart(values, currentSlot);
      if (futureError) return { error: futureError };
    }
    return { values: values };
  }
  function apiErrorText(error) {
    if (error.status === 401) return "Your session expired. Sign in again.";
    if (error.status === 403) return "You do not have permission to change this record.";
    if (error.status === 409) return "This change conflicts with an active reservation or schedule entry. Refresh and try again.";
    if (error.status === 422) return "Please check the form: " + error.message;
    if (error.status === 503) return "This action is temporarily unavailable. Please try again.";
    return error.message || "Could not save your changes. Please try again.";
  }
  function hasCourtLoadError() {
    return Object.keys(courtResources).some(function (key) { return courtResources[key].status === "error"; });
  }
  function saveApiRecord(form) {
    var resource = form.dataset.crudResource;
    var allowed = authUser && ((authUser.role === "ADMIN" && ["sports", "venues", "courts", "slots"].indexOf(resource) >= 0) || (authUser.role === "OWNER" && resource !== "sports"));
    if (!allowed) {
      toast("This action is not available for the current role.");
      return;
    }
    var parsed = apiFormValues(form, resource);
    if (parsed.error) { toast(parsed.error); return; }
    var id = form.dataset.crudId;
    var path = "/api/v1/" + resourceForApi(resource) + (id ? "/" + encodeURIComponent(id) : "");
    var submit = form.querySelector('[type="submit"]');
    if (submit) { submit.disabled = true; submit.textContent = "Saving..."; }
    var request = id ? window.CourtApi.put(path, parsed.values) : window.CourtApi.post(path, parsed.values);
    request.then(function () {
      crudFormState = null;
      return loadCourtResources(true);
    }).then(function () {
      var action = (id ? "Updated " : "Created ") + ({ sports: "sport", venues: "venue", courts: "court", slots: "time slot" }[resource]);
      toast(hasCourtLoadError() ? action + ", but the refreshed list has a load error. Use Retry to reload it." : action + ".");
    }).catch(function (error) {
      toast(apiErrorText(error));
      render();
    });
  }
  function deactivateDemoRecord(resource, id) {
    if (dataMode !== "demo") {
      var allowed = authUser && ((authUser.role === "ADMIN" && ["sports", "venues", "courts", "slots"].indexOf(resource) >= 0) || (authUser.role === "OWNER" && resource !== "sports"));
      if (!allowed) {
        toast("This action is not available for the current role.");
        return;
      }
      var apiLabel = ({ sports: "sport", venues: "venue", courts: "court", slots: "time slot" }[resource]);
      showActionConfirmation("Deactivate " + apiLabel, "This record will be marked inactive.", "Deactivate", function () {
        toast("Deactivating " + apiLabel + "...");
        window.CourtApi.delete("/api/v1/" + resourceForApi(resource) + "/" + encodeURIComponent(id)).then(function () {
          crudFormState = null;
          return loadCourtResources(true);
        }).then(function () {
          toast(hasCourtLoadError() ? "Deactivated " + apiLabel + ", but the refreshed list could not be loaded. Use Retry to reload it." : apiLabel + " deactivated.");
        }).catch(function (error) { toast(apiErrorText(error)); });
      });
      return;
    }
    var records = recordsFor(resource);
    var record = records.find(function (item) { return String(item.id) === String(id); });
    if (!record) return;
    var label = ({ sports: "sport", venues: "venue", courts: "court", slots: "time slot" }[resource]);
    showActionConfirmation("Deactivate " + label, "This Demo record will be marked inactive. No API request will be sent.", "Deactivate", function () {
      record.is_active = false;
      crudFormState = null;
      render();
      toast("Demo " + label + " deactivated. No API request was sent.");
    });
  }
  function showActionConfirmation(title, message, confirmLabel, onConfirm) {
    var host = document.getElementById("action-confirmation-modal-host");
    if (!host) { host = document.createElement("div"); host.id = "action-confirmation-modal-host"; document.body.appendChild(host); }
    host.innerHTML = '<div class="modal fade" id="action-confirmation-modal" tabindex="-1" aria-labelledby="action-confirmation-title" aria-hidden="true"><div class="modal-dialog modal-dialog-centered"><div class="modal-content"><div class="modal-header"><h2 class="modal-title fs-6" id="action-confirmation-title">' + esc(title) + '</h2><button type="button" class="btn-close" data-modal-close aria-label="Close"></button></div><div class="modal-body">' + esc(message) + '</div><div class="modal-footer"><button type="button" class="btn btn-outline-secondary" data-modal-close>Cancel</button><button type="button" class="btn btn-danger" data-confirm-action>' + esc(confirmLabel) + '</button></div></div></div></div>';
    var modal = document.getElementById("action-confirmation-modal");
    modal.querySelector("[data-confirm-action]").addEventListener("click", function () {
      closeManagedModal(modal);
      onConfirm();
    });
    showManagedModal(modal, host);
  }
  function wireActions() {
    document.querySelectorAll("[data-registry-tab]").forEach(function (button) {
      button.addEventListener("click", function () {
        registryTab = button.dataset.registryTab;
        crudFormState = null;
        render();
      });
    });
    var registrySearch = document.querySelector("[data-registry-search]");
    if (registrySearch) registrySearch.addEventListener("input", applyRegistryFilters);
    document.querySelectorAll("[data-registry-sport-filter], [data-registry-active-filter], [data-registry-status], [data-registry-venue-filter]").forEach(function (el) {
      el.addEventListener("change", applyRegistryFilters);
    });
    var modeSelect = document.getElementById("court-data-mode");
    if (modeSelect) modeSelect.addEventListener("change", function () {
      var nextMode = modeSelect.value;
      if (currentRoute() === "qr-checkin" && (qrScanner || scannerInstance || scannerStarting)) {
        modeSelect.disabled = true;
        stopQrScanner().then(function (stopped) {
          if (stopped) {
            dataMode = nextMode; scannerState = "idle"; scanResult = null; crudFormState = null;
            if (nextMode === "api" && currentRoute() === "owner-bookings") ownerBookingsState.status = "idle";
            render();
          } else {
            modeSelect.disabled = false; modeSelect.value = dataMode;
          }
        });
        return;
      }
      dataMode = nextMode;
      scannerState = "idle";
      scanResult = null;
      crudFormState = null;
      if (nextMode === "api" && currentRoute() === "owner-bookings") ownerBookingsState.status = "idle";
      render();
    });
    document.querySelectorAll("[data-crud-open]").forEach(function (el) {
      el.addEventListener("click", function () {
        crudFormState = { resource: el.dataset.crudOpen, id: el.dataset.crudId || null };
        render();
      });
    });
    document.querySelectorAll("[data-crud-cancel]").forEach(function (el) {
      el.addEventListener("click", function () {
        crudFormState = null;
        render();
      });
    });
    document.querySelectorAll("[data-crud-form]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (!form.checkValidity()) { form.reportValidity(); return; }
        if (dataMode === "demo") saveDemoRecord(form);
        else saveApiRecord(form);
      });
    });
    document.querySelectorAll("[data-crud-delete]").forEach(function (el) {
      el.addEventListener("click", function () { deactivateDemoRecord(el.dataset.crudDelete, el.dataset.crudId); });
    });
    document.querySelectorAll("[data-toast]").forEach(function (el) {
      el.addEventListener("click", function (event) {
        if (el.tagName === "A") event.preventDefault();
        toast(el.dataset.toast);
      });
    });
    document.querySelectorAll("[data-pending-auth]").forEach(function (el) {
      el.addEventListener("click", function () {
        toast("This write action is not available for the current account.");
      });
    });
    document.querySelectorAll("[data-court-retry], [data-court-refresh]").forEach(function (el) {
      el.addEventListener("click", function () {
        if (dataMode === "demo") {
          render();
          toast("Demo catalogue refreshed from current in-memory data. No changes were reset.");
        } else {
          if (currentRoute() === "admin-dashboard") loadAdminCatalogueSummary(true);
          else loadCourtResources(true);
        }
      });
    });
    document.querySelectorAll("[data-resource-detail]").forEach(function (el) {
      el.addEventListener("click", function () {
        var resource = el.dataset.resourceDetail;
        var id = encodeURIComponent(el.dataset.resourceId);
        if (dataMode === "demo") {
          var collection = resource === "time-slots" ? "slots" : resource;
          var item = recordsFor(collection).find(function (record) { return String(record.id) === String(id); });
          if (item) showResourceDetails(resource, item);
          else toast("Demo record was not found.");
          return;
        }
        window.CourtApi.get("/api/v1/" + resource + "/" + id).then(function (item) {
          showResourceDetails(resource, item);
        }).catch(function (error) {
          toast("Could not load details: " + (error.message || "Connection error."));
        });
      });
    });
    document.querySelectorAll("[data-table-search], [data-status-filter], [data-account-role], [data-account-status]").forEach(function (el) {
      el.addEventListener("input", filterRows);
      el.addEventListener("change", filterRows);
    });
    document.querySelectorAll("[data-filter-reset]").forEach(function (button) {
      button.addEventListener("click", function () {
        var toolbar = button.closest("[data-filter-toolbar]");
        if (!toolbar) return;
        toolbar.querySelectorAll("input[type=search]").forEach(function (input) { input.value = ""; });
        toolbar.querySelectorAll("select").forEach(function (select) { select.value = ""; });
        filterRows();
      });
    });
    var accountRows = document.getElementById("admin-account-rows");
    if (accountRows) accountRows.addEventListener("click", function (event) {
      var button = event.target.closest("[data-account-detail]");
      if (!button) return;
      var account = data.people.find(function (row) { return row[0] === button.dataset.accountDetail; });
      if (account) showAccountDetails(account);
    });
    var adminUserSearch = document.querySelector("[data-admin-user-q]");
    var adminUserRole = document.querySelector("[data-admin-user-role]");
    var adminUserActive = document.querySelector("[data-admin-user-active]");
    function updateAdminUserFilters() {
      adminUsersFilters = { page: 1, page_size: 25, q: adminUserSearch ? adminUserSearch.value.trim() : "", role: adminUserRole ? adminUserRole.value : "", is_active: adminUserActive ? adminUserActive.value : "" };
      loadAdminPage("users", adminUsersFilters);
    }
    if (adminUserSearch) adminUserSearch.addEventListener("change", updateAdminUserFilters);
    if (adminUserRole) adminUserRole.addEventListener("change", updateAdminUserFilters);
    if (adminUserActive) adminUserActive.addEventListener("change", updateAdminUserFilters);
    var adminBookingId = document.querySelector("[data-admin-booking-id]");
    var adminBookingStatus = document.querySelector("[data-admin-booking-status]");
    function updateAdminBookingFilters() {
      function value(field) { var input = document.querySelector('[data-admin-booking-field="' + field + '"]'); return input ? input.value : ""; }
      adminBookingsFilters = { page: 1, page_size: 25, booking_id: adminBookingId ? adminBookingId.value.trim() : "", status: adminBookingStatus ? adminBookingStatus.value : "", date_from: adminBookingsFilters.date_from, date_to: adminBookingsFilters.date_to, venue_id: value("venue_id"), court_id: value("court_id"), owner_id: value("owner_id"), user_id: value("user_id") };
      loadAdminPage("bookings", adminBookingsFilters);
    }
    [adminBookingId, adminBookingStatus].forEach(function (control) {
      if (control) control.addEventListener(control.type === "search" ? "change" : "change", updateAdminBookingFilters);
      if (control && control.type === "search") control.addEventListener("keydown", function (event) { if (event.key === "Enter") updateAdminBookingFilters(); });
    });
    document.querySelectorAll("[data-admin-booking-field]").forEach(function (control) { control.addEventListener("change", updateAdminBookingFilters); });
    var adminCheckinBooking = document.querySelector("[data-admin-checkin-booking]");
    function updateAdminCheckinFilters() {
      function value(field) { var input = document.querySelector('[data-admin-checkin-field="' + field + '"]'); return input ? input.value : ""; }
      adminCheckinsFilters = { page: 1, page_size: 25, booking_id: adminCheckinBooking ? adminCheckinBooking.value.trim() : "", date_from: adminCheckinsFilters.date_from, date_to: adminCheckinsFilters.date_to, venue_id: value("venue_id"), court_id: value("court_id"), checked_in_by: value("checked_in_by") };
      loadAdminPage("checkins", adminCheckinsFilters);
    }
    [adminCheckinBooking].forEach(function (control) {
      if (control) control.addEventListener("change", updateAdminCheckinFilters);
      if (control && control.type === "search") control.addEventListener("keydown", function (event) { if (event.key === "Enter") updateAdminCheckinFilters(); });
    });
    document.querySelectorAll("[data-admin-checkin-field]").forEach(function (control) { control.addEventListener("change", updateAdminCheckinFilters); });
    document.querySelectorAll("[data-admin-page]").forEach(function (button) {
      button.addEventListener("click", function () {
        var kind = button.dataset.adminPage;
        var filters = kind === "users" ? adminUsersFilters : (kind === "bookings" ? adminBookingsFilters : adminCheckinsFilters);
        filters.page = Number(button.dataset.page) || 1;
        loadAdminPage(kind, filters);
      });
    });
    document.querySelectorAll("[data-admin-retry]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (currentRoute() === "people") loadAdminPage("users", adminUsersFilters);
        else if (currentRoute() === "admin-bookings") loadAdminPage("bookings", adminBookingsFilters);
        else loadAdminPage("checkins", adminCheckinsFilters);
      });
    });
    document.querySelectorAll("[data-admin-filter-clear]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (button.dataset.adminFilterClear === "bookings") {
          adminBookingsFilters = { page: 1, page_size: 25, booking_id: "", status: "", date_from: "", date_to: "", venue_id: "", court_id: "", owner_id: "", user_id: "" };
          render();
          loadAdminPage("bookings", adminBookingsFilters);
        } else {
          adminCheckinsFilters = { page: 1, page_size: 25, booking_id: "", date_from: "", date_to: "", venue_id: "", court_id: "", checked_in_by: "" };
          render();
          loadAdminPage("checkins", adminCheckinsFilters);
        }
      });
    });
    document.querySelectorAll("[data-admin-user-detail]").forEach(function (button) {
      button.addEventListener("click", function () {
        window.AdminManagementApi.getUser(button.dataset.adminUserDetail).then(function (user) {
          showAdminRecordDetails("User account " + user.id, user, [["id", "ID"], ["full_name", "Full name"], ["email", "Email"], ["phone", "Phone"], ["role", "Role"], ["is_active", "Active"], ["created_at", "Created"]]);
        }).catch(function (error) { toast(adminApiErrorMessage(error)); });
      });
    });
    document.querySelectorAll("[data-admin-booking-detail]").forEach(function (button) {
      button.addEventListener("click", function () {
        window.AdminManagementApi.getBooking(button.dataset.adminBookingDetail).then(function (booking) {
          showAdminRecordDetails("Booking " + booking.id, booking, [["id", "ID"], ["user_id", "User ID"], ["owner_id", "Owner ID"], ["venue_id", "Venue ID"], ["court_id", "Court ID"], ["time_slot_id", "Time Slot ID"], ["slot_date", "Date"], ["start_time", "Start time"], ["end_time", "End time"], ["status", "Status"], ["total_amount", "Total amount"], ["checked_in_by", "Checked in by"], ["checked_in_at", "Checked in at"], ["completed_at", "Completed at"], ["created_at", "Created"]]);
        }).catch(function (error) { toast(adminApiErrorMessage(error)); });
      });
    });
    document.querySelectorAll("[data-admin-user-status]").forEach(function (button) {
      button.addEventListener("click", function () {
        var nextActive = button.dataset.active !== "true";
        function saveStatus() {
          button.disabled = true;
          window.AdminManagementApi.setUserActive(button.dataset.userId, nextActive).then(function () {
            toast(nextActive ? "Account activated." : "Account deactivated.");
            return loadAdminPage("users", adminUsersFilters);
          }).catch(function (error) { toast(adminApiErrorMessage(error)); }).finally(function () { button.disabled = false; });
        }
        if (nextActive) saveStatus();
        else showActionConfirmation("Deactivate account", "This prevents new login. Existing tokens may remain valid until they expire.", "Deactivate", saveStatus);
      });
    });
    var bookingSearchInput = document.querySelector("[data-booking-search]");
    if (bookingSearchInput) bookingSearchInput.addEventListener("input", applyBookingFilters);
    var bookingStatusInput = document.querySelector("[data-booking-status]");
    if (bookingStatusInput) bookingStatusInput.addEventListener("change", function () {
      bookingStatus = bookingStatusInput.value || "";
      if (dataMode === "demo") applyBookingFilters();
      else loadOwnerBookings();
    });
    var bookingVenueInput = document.querySelector("[data-booking-venue]");
    if (bookingVenueInput) bookingVenueInput.addEventListener("change", function () {
      bookingVenueId = bookingVenueInput.value || "";
      loadOwnerBookings();
    });
    var bookingClear = document.querySelector("[data-booking-clear]");
    if (bookingClear) bookingClear.addEventListener("click", function () {
      bookingSearch = ""; bookingDate = ""; bookingStatus = ""; bookingVenueId = "";
      if (bookingSearchInput) bookingSearchInput.value = "";
      var bookingDatePicker = document.querySelector('[data-calendar-picker][data-calendar-id="booking-filter"]');
      if (bookingDatePicker) { setCalendarDate(bookingDatePicker, ""); closeCalendarPicker(bookingDatePicker, false); }
      if (bookingStatusInput) bookingStatusInput.value = "";
      if (bookingVenueInput) bookingVenueInput.value = "";
      if (dataMode === "demo") applyBookingFilters();
      else loadOwnerBookings();
      if (bookingSearchInput) bookingSearchInput.focus();
    });
    document.querySelectorAll("[data-booking-retry]").forEach(function (button) {
      button.addEventListener("click", loadOwnerBookings);
    });
    var bookingRowsHost = document.getElementById("owner-booking-rows");
    if (bookingRowsHost) bookingRowsHost.addEventListener("click", function (event) {
      var detailButton = event.target.closest("[data-booking-detail]");
      var completeButton = event.target.closest("[data-booking-complete]");
      if (detailButton) {
        if (dataMode === "demo") {
          var booking = demoBookings.find(function (item) { return item.id === detailButton.dataset.bookingDetail; });
          if (booking) bookingDetail(booking);
        } else loadOwnerBookingDetail(detailButton.dataset.bookingDetail);
      } else if (completeButton) {
        if (dataMode === "demo") completeDemoBooking(completeButton.dataset.bookingComplete);
        else {
          var apiBooking = ownerBookingsState.data.find(function (item) { return String(item.id) === completeButton.dataset.bookingComplete; });
          if (apiBooking) completeOwnerBooking(apiBooking, completeButton);
        }
      }
    });
    var scannerStart = document.querySelector("[data-scanner-start]");
    if (scannerStart) scannerStart.addEventListener("click", startQrScanner);
    var scannerStop = document.querySelector("[data-scanner-stop]");
    if (scannerStop) scannerStop.addEventListener("click", function () { stopQrScanner(); });
    var demoQrSubmit = document.querySelector("[data-demo-qr-submit]");
    if (demoQrSubmit) demoQrSubmit.addEventListener("click", function () { checkDemoQr((document.getElementById("demo-qr-token").value || "").trim()); });
    var ownerQrSubmit = document.querySelector("[data-owner-qr-submit]");
    if (ownerQrSubmit) ownerQrSubmit.addEventListener("click", function () { submitOwnerCheckin((document.getElementById("owner-qr-token").value || "").trim()); });
    document.querySelectorAll("[data-copy-qr]").forEach(function (el) {
      el.addEventListener("click", function () {
        var token = el.dataset.copyQr;
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(token).then(function () { toast("Demo QR token copied."); }).catch(function () { toast("Copy was blocked; select the token text to copy it."); });
        else toast("Select the Demo token text and copy it manually.");
      });
    });
    document.querySelectorAll("[data-schedule-search], [data-schedule-court], [data-schedule-venue], [data-schedule-status]").forEach(function (el) {
      var applyFilters = function () {
        scheduleFilters.search = (document.querySelector("[data-schedule-search]") || {}).value || "";
        var dateFilter = document.querySelector("[data-schedule-date]");
        scheduleFilters.date = dateFilter ? dateFilter.dataset.dateValue || "" : "";
        scheduleFilters.courtId = (document.querySelector("[data-schedule-court]") || {}).value || "";
        scheduleFilters.venueId = (document.querySelector("[data-schedule-venue]") || {}).value || "";
        scheduleFilters.status = (document.querySelector("[data-schedule-status]") || {}).value || "";
        renderKeepingFocus(el);
      };
      el.addEventListener(el.matches("input[type=search]") ? "input" : "change", applyFilters);
    });
    document.querySelectorAll("[data-calendar-picker]").forEach(function (picker) {
      wireCalendarPicker(picker);
      if (calendarOpenIds[picker.dataset.calendarId]) {
        var popover = picker.querySelector("[data-calendar-popover]");
        var toggle = picker.querySelector("[data-calendar-toggle]");
        if (popover && toggle) { popover.hidden = false; picker.dataset.calendarOpen = "true"; toggle.setAttribute("aria-expanded", "true"); updateCalendarGrid(picker); }
      }
    });
    var scheduleReset = document.querySelector("[data-schedule-reset]");
    if (scheduleReset) scheduleReset.addEventListener("click", function () {
      scheduleFilters = scheduleUtils.emptyFilters();
      calendarViews["schedule-filter"] = null;
      calendarOpenIds["schedule-filter"] = false;
      render();
    });
    var slotVenue = document.querySelector('[data-crud-form][data-crud-resource="slots"] [name="venue_id"]');
    var slotCourt = document.querySelector("[data-slot-court]");
    if (slotVenue && slotCourt) slotVenue.addEventListener("change", function () {
      var availableCourts = scheduleUtils.courtsForVenue(courtResources.courts.data, slotVenue.value);
      if (dataMode === "demo") availableCourts = scheduleUtils.courtsForVenue(demoCourtData.courts, slotVenue.value);
      var previousCourtId = slotCourt.value;
      var keepPrevious = availableCourts.some(function (court) { return String(court.id) === String(previousCourtId); });
      slotCourt.innerHTML = '<option value="">' + (slotVenue.value ? (availableCourts.length ? "Choose court" : "No courts for this venue") : "Choose a venue first") + '</option>' + availableCourts.map(function (court) {
        return '<option value="' + esc(court.id) + '" ' + (keepPrevious && String(court.id) === String(previousCourtId) ? "selected" : "") + '>' + esc(court.name) + '</option>';
      }).join("");
    });
    var scheduleRetry = document.querySelector("[data-schedule-retry]");
    if (scheduleRetry) scheduleRetry.addEventListener("click", refreshSchedule);
    var verify = document.getElementById("verify-booking");
    if (verify) verify.addEventListener("click", function () {
      var code = document.getElementById("booking-token").value.trim().toUpperCase();
      if (code === "BK-2047") document.getElementById("verify-result").classList.remove("d-none");
      else toast(code ? "No matching sample booking. Try BK-2047." : "Enter a booking code to continue.");
    });
    var profile = document.getElementById("profile-form");
    if (profile) profile.addEventListener("submit", function (event) {
      event.preventDefault();
      toast("Profile changes are shown in this demo only.");
    });
  }
  function render() {
    var active = currentRoute();
    if (active === "login") {
      if (authUser) { location.hash = "#" + homeRouteForRole(authUser.role); return; }
      if (demoRole) { location.hash = "#" + homeRouteForRole(demoRole); return; }
      if (window.CourtApi.hasAccessToken()) { restoreAuthSession(); document.getElementById("app").innerHTML = '<main class="login-page"><section class="login-form-side"><div class="login-card">Checking your session...</div></section></main>'; return; }
      renderLogin(); return;
    }
    if (!demoRole && !authUser && window.CourtApi.hasAccessToken()) {
      restoreAuthSession();
      document.getElementById("app").innerHTML = '<main class="login-page"><section class="login-form-side"><div class="login-card">Checking your session...</div></section></main>';
      return;
    }
    if (!demoRole && !authUser) { location.hash = "#/login"; renderLogin(); return; }
    var role = currentRole();
    var requestedAdmin = active.indexOf("admin-") === 0 || active === "people" || active === "checkins";
    if (role === "OWNER" && requestedAdmin) { location.hash = "#/dashboard"; return; }
    if (role === "ADMIN" && !requestedAdmin) { location.hash = "#/admin-dashboard"; return; }
    if (active === "qr-checkin" && (scannerStarting || qrScanner || scannerInstance || scannerStopPromise) && document.getElementById("qr-reader")) {
      updateScannerState();
      updateScannerResult();
      return;
    }
    var admin = active.indexOf("admin-") === 0 || active === "people" || active === "checkins";
    if (!info[active]) active = admin ? "admin-dashboard" : "dashboard";
    var content = pageFor(active);
    var ownerModeScreens = ["dashboard", "venues", "schedule", "owner-bookings", "qr-checkin", "revenue"];
    var adminModeScreens = ["admin-dashboard", "admin-venues", "admin-schedule", "admin-bookings", "checkins", "people"];
    if (!admin && ownerModeScreens.indexOf(active) >= 0) content = modeToolbar() + content;
    if (admin && adminModeScreens.indexOf(active) >= 0) content = modeToolbar() + content;
    renderShell(content, admin, active);
    wireActions();
    if (active === "venues" || active === "admin-venues") applyRegistryFilters();
    var courtScreens = ["dashboard", "venues", "admin-venues", "schedule", "admin-schedule"];
    if (active === "qr-checkin" && dataMode === "demo" && !window.Html5Qrcode) {
      window.addEventListener("load", function () { updateScannerState(); }, { once: true });
    }
    if (dataMode === "api" && courtScreens.indexOf(active) >= 0 && Object.keys(courtResources).every(function (key) { return courtResources[key].status === "idle"; })) {
      loadCourtResources(false);
    }
    if (active === "admin-dashboard" && dataMode === "api" && adminCatalogueSummary.status === "idle") loadAdminCatalogueSummary(false);
    if (active === "owner-bookings" && dataMode === "api" && ownerBookingsState.status === "idle") loadOwnerBookings();
    if (active === "people" && dataMode === "api" && adminUsersState.status === "idle") loadAdminPage("users", adminUsersFilters);
    if (active === "admin-bookings" && dataMode === "api" && adminBookingsState.status === "idle") loadAdminPage("bookings", adminBookingsFilters);
    if (active === "checkins" && dataMode === "api" && adminCheckinsState.status === "idle") loadAdminPage("checkins", adminCheckinsFilters);
  }
  function restoreAuthSession() {
    if (authRestorePromise) return authRestorePromise;
    authRestorePromise = window.CourtApi.get("/api/v1/users/me").then(function (user) {
      var role = String(user && user.role || "").toUpperCase();
      if (role !== "OWNER" && role !== "ADMIN") throw new Error("This Management Web is available to OWNER and ADMIN accounts.");
      authUser = user;
      demoRole = "";
      dataMode = "api";
      try { window.sessionStorage.removeItem("managementDemoRole"); } catch (error) { /* storage may be unavailable */ }
      if (currentRoute() === "login") location.hash = "#" + homeRouteForRole(role);
      else render();
    }).catch(function (error) {
      window.CourtApi.clearAccessToken();
      authUser = null;
      authRestorePromise = null;
      authMessage = error.message || "Your session has expired. Please sign in again.";
      location.hash = "#/login";
      renderLogin();
    }).finally(function () { authRestorePromise = null; });
    return authRestorePromise;
  }
  var renderedRoute = currentRoute();
  var navigationStopPromise = null;
  window.addEventListener("hashchange", function () {
    var nextRoute = currentRoute();
    if (nextRoute !== renderedRoute) calendarOpenIds = {};
    if (navigationStopPromise) return;
    if (renderedRoute === "qr-checkin" && nextRoute !== "qr-checkin") {
      navigationStopPromise = stopQrScanner().then(function (stopped) {
        if (!stopped) {
          renderedRoute = "qr-checkin";
          if (currentRoute() !== "qr-checkin") location.hash = "#/qr-checkin";
          return;
        }
        renderedRoute = currentRoute();
        scannerState = "idle";
        render();
      }).catch(function (error) {
        scannerState = "error";
        scanResult = { ok: false, title: "Camera stop error", message: error && error.message ? error.message : "Could not stop the camera safely. Retry Stop Camera.", booking: null };
        updateScannerState("ERROR");
        updateScannerResult();
        renderedRoute = "qr-checkin";
        if (currentRoute() !== "qr-checkin") location.hash = "#/qr-checkin";
      }).finally(function () { navigationStopPromise = null; });
      return;
    }
    if (nextRoute === "qr-checkin") {
      renderedRoute = nextRoute;
      render();
      return;
    }
    renderedRoute = nextRoute;
    render();
  });
  window.addEventListener("beforeunload", function () { stopQrScanner(); });
  document.addEventListener("visibilitychange", function () { if (document.hidden && (qrScanner || scannerInstance || scannerStarting)) stopQrScanner(); });
  window.addEventListener("management:unauthorized", function () {
    if (!authUser || !window.CourtApi.hasAccessToken()) return;
    function expireSession() {
      clearSession();
      dataMode = "api";
      authMessage = "Your session expired. Please sign in again.";
      location.hash = "#/login";
      renderLogin();
    }
    if (currentRoute() === "qr-checkin" && (qrScanner || scannerInstance || scannerStarting)) {
      stopQrScanner().then(function (stopped) {
        if (stopped) expireSession();
        else toast("Your session expired. Stop the camera safely, then sign in again.");
      });
    } else expireSession();
  });
  document.addEventListener("qrscannerloaderror", function () {
    var start = document.querySelector("[data-scanner-start]");
    if (start && currentRoute() === "qr-checkin") { start.disabled = false; start.title = window.Html5QrcodeLoadError; }
  });
  document.addEventListener("click", function (event) {
    document.querySelectorAll('[data-calendar-picker][data-calendar-open="true"]').forEach(function (picker) {
      if (!picker.contains(event.target)) closeCalendarPicker(picker, false);
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") document.querySelectorAll('[data-calendar-picker][data-calendar-open="true"]').forEach(function (picker) { closeCalendarPicker(picker, true); });
  });
  render();
})();
