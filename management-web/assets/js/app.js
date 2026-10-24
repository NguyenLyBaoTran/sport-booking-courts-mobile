(function () {
  "use strict";
  var data = window.BookingMockData;
  var dataMode = "api";
  var demoCourtData = window.CourtDemoData.create();
  var demoBookings = window.BookingDemoData.create();
  var bookingSearch = "";
  var bookingDate = "";
  var bookingStatus = "";
  var venueSearch = "";
  var courtSearch = "";
  var qrScanner = null;
  var scannerInstance = null;
  var scannerStarting = false;
  var scannerStartPromise = null;
  var scannerStopPromise = null;
  var scannerEpoch = 0;
  var scannerState = "idle";
  var lastScannedText = "";
  var lastScanAt = 0;
  var scanProcessing = false;
  var scanResult = null;
  var crudFormState = null;
  var courtResources = {
    sports: { status: "idle", data: [], error: "" },
    venues: { status: "idle", data: [], error: "" },
    courts: { status: "idle", data: [], error: "" },
    slots: { status: "idle", data: [], error: "" }
  };
  var scheduleState = { status: "idle", data: [], error: "" };
  var courtLoadPromise = null;
  var scheduleFilters = { date: "", courtId: "", venueId: "" };
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
    ["admin-bookings", "Bookings", "bi-journal-check"],
    ["checkins", "Check-ins", "bi-qr-code"],
    ["admin-profile", "Profile", "bi-person-circle"]
  ];
  var info = {
    dashboard: ["Owner dashboard", "Welcome back, Nguyễn Văn A", "Live Court Service catalogue; booking and revenue APIs are not connected."],
    venues: ["Venue management", "Venue & Court", "Manage your sports venues, courts, and availability."],
    schedule: ["Court operations", "Facility Schedule", "Review your court availability for this week."],
    "owner-bookings": ["Owner operations", "Bookings Management", "Track and review reservations across your venues."],
    "qr-checkin": ["Front desk", "QR Check-in Terminal", "Verify a customer booking before check-in."],
    revenue: ["Business overview", "Revenue & Payouts", "Sample revenue summary for your venues."],
    "owner-profile": ["Account settings", "Owner Profile", "Manage the contact details associated with your account."],
    "admin-dashboard": ["System overview", "Admin Dashboard", "Live Court Service catalogue; Booking and revenue APIs are not connected."],
    people: ["Directory", "Users & Court Owners", "Review customer and court owner accounts."],
    "admin-venues": ["Platform registry", "Venues & Courts Registry", "Review venue listings and court status."],
    "admin-bookings": ["Platform activity", "Global Bookings", "Search and monitor bookings across all venues."],
    checkins: ["Platform activity", "Check-in Management", "Review recent booking check-ins."],
    "admin-profile": ["Account settings", "Admin Profile", "Manage your administrator account details."]
  };
  var statSets = {
    dashboard: [["bi-calendar-check", "Today’s bookings"], ["bi-people", "Active customers"], ["bi-building", "My venues"], ["bi-currency-exchange", "Revenue this month"]],
    "admin-dashboard": [["bi-people", "Total users"], ["bi-buildings", "Court owners"], ["bi-journal-check", "Bookings today"], ["bi-currency-exchange", "Gross booking value"]],
    venues: [["bi-buildings", "My venues"], ["bi-grid-3x3", "Total courts"], ["bi-clock-history", "Available slots"], ["bi-check-circle", "Open venues"]],
    bookings: [["bi-journal-check", "Bookings today"], ["bi-currency-exchange", "Revenue today"], ["bi-check2-circle", "Checked in"], ["bi-hourglass-split", "Needs attention"]],
    revenue: [["bi-currency-exchange", "Revenue this month"], ["bi-graph-up-arrow", "Revenue this week"], ["bi-wallet2", "Pending payout"], ["bi-calendar2-check", "Paid out this month"]],
    people: [["bi-people", "Total accounts"], ["bi-person-check", "Active users"], ["bi-building-check", "Court owners"], ["bi-person-exclamation", "Pending review"]],
    "admin-venues": [["bi-buildings", "Total venues"], ["bi-grid-3x3", "Courts listed"], ["bi-check-circle", "Open venues"], ["bi-hourglass-split", "Needs review"]],
    checkins: [["bi-qr-code", "Check-ins today"], ["bi-shield-check", "Verified"], ["bi-building", "Active venues"], ["bi-exclamation-circle", "Manual reviews"]],
    "court-overview": [["bi-trophy", "Sports"], ["bi-buildings", "Venues"], ["bi-grid-3x3", "Courts"], ["bi-clock-history", "Active slot records"]],
    "court-registry": [["bi-trophy", "Sports"], ["bi-buildings", "Venues"], ["bi-grid-3x3", "Courts"], ["bi-check-circle", "Active venues"]]
  };

  function currentRoute() {
    return (location.hash.replace(/^#\/?/, "") || "login").toLowerCase();
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
    var message = demo
      ? "Changes stay in this browser tab memory and reset when the page is reloaded. No API request is sent."
      : "Live GET data from Court Service. Save and deactivate are disabled until JWT integration.";
    return '<section class="court-mode-bar" aria-label="Court data mode"><div><strong>' +
      (demo ? "Demo Mode" : "API Mode") + '</strong><small>' + message +
      '</small></div><label class="small mb-0" for="court-data-mode">Data mode</label><select id="court-data-mode" class="form-select" aria-label="Select data mode"><option value="api" ' +
      (!demo ? "selected" : "") + '>API Mode — real GET, writes disabled</option><option value="demo" ' +
      (demo ? "selected" : "") + '>Demo Mode — in-memory sample data</option></select></section>';
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
  function resourceQuery(values) {
    var query = new URLSearchParams();
    Object.keys(values).forEach(function (key) {
      if (values[key] !== "" && values[key] !== null && values[key] !== undefined) query.set(key, values[key]);
    });
    return query.toString();
  }
  function fetchCollection(path) {
    return window.CourtApi.get(path).then(function (items) {
      if (!Array.isArray(items)) throw new Error("The API returned an unexpected list response.");
      return items;
    });
  }
  function loadCourtResources(force) {
    if (courtLoadPromise) return courtLoadPromise;
    if (!force && Object.keys(courtResources).every(function (key) { return courtResources[key].status !== "idle"; })) return Promise.resolve();
    var requests = {
      sports: "/api/v1/sports",
      venues: "/api/v1/venues",
      courts: "/api/v1/courts",
      slots: "/api/v1/time-slots"
    };
    Object.keys(requests).forEach(function (key) {
      courtResources[key] = { status: "loading", data: force ? courtResources[key].data : [], error: "" };
    });
    courtLoadPromise = Promise.all(Object.keys(requests).map(function (key) {
      return fetchCollection(requests[key]).then(function (items) {
        courtResources[key] = { status: "loaded", data: items, error: "" };
      }).catch(function (error) {
        courtResources[key] = { status: "error", data: [], error: error.message || "Could not load data." };
      });
    })).then(function () {
      scheduleState = {
        status: courtResources.slots.status,
        data: courtResources.slots.data,
        error: courtResources.slots.error
      };
    }).finally(function () {
      courtLoadPromise = null;
      render();
    });
    render();
    return courtLoadPromise;
  }
  function refreshSchedule() {
    if (dataMode === "demo") {
      render();
      return;
    }
    var query = resourceQuery({ slot_date: scheduleFilters.date, court_id: scheduleFilters.courtId });
    var path = "/api/v1/time-slots" + (query ? "?" + query : "");
    scheduleState = { status: "loading", data: [], error: "" };
    render();
    fetchCollection(path).then(function (items) {
      scheduleState = { status: "loaded", data: items, error: "" };
    }).catch(function (error) {
      scheduleState = { status: "error", data: [], error: error.message || "Could not load time slots." };
    }).finally(render);
  }
  function retryButton() {
    return '<button class="btn btn-sm btn-outline-secondary" data-court-retry>Retry</button>';
  }
  function pendingWriteNotice() {
    if (dataMode === "demo") {
      return '<div class="alert alert-info py-2 small" role="status"><strong>Demo Mode:</strong> Changes affect only the in-memory sample data. Reload the page to restore the starter data.</div>';
    }
    return '<div class="alert alert-warning py-2 small" role="status"><strong>API Mode:</strong> GET uses Court Service data. Add, edit, and deactivate are read-only previews until S1 provides the JWT contract; no write request is sent.</div>';
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
    return '<div class="alert alert-danger d-flex justify-content-between align-items-center gap-2" role="alert"><span>' + (gatewayOffline ? "Cannot connect to API Gateway. Start the API Gateway and Court Service, then retry." : "Could not load " + esc(label) + ": " + esc(error || "Connection error.")) + '</span>' + retryButton() + "</div>";
  }
  function crudOpenButton(resource, id, label, style) {
    return '<button type="button" class="btn btn-sm ' + (style || "btn-outline-secondary") + '" data-crud-open="' + esc(resource) + '" data-crud-id="' + esc(id === undefined ? "" : id) + '">' + esc(label) + "</button>";
  }
  function crudDeleteButton(resource, id) {
    return '<button type="button" class="btn btn-sm btn-outline-danger" data-crud-delete="' + esc(resource) + '" data-crud-id="' + esc(id) + '" ' + (dataMode === "api" ? 'disabled title="JWT integration is pending"' : "") + '>Delete</button>';
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
      if (dataMode === "api") fields += formInput("Owner ID", "owner_id", record && record.owner_id, "number", 'min="1" step="1" required');
      else fields += '<div class="crud-field-full small text-secondary">Owner: Demo session (not a real User Service account)</div>';
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
      fields = formSelect("Court", "court_id", resources.courts.data, record && record.court_id, function (item) { return item.name; }) +
        formInput("Date", "slot_date", record && record.slot_date, "date", "required") +
        formInput("Start time", "start_time", record && apiTime(record.start_time), "time", 'step="60" required') +
        formInput("End time", "end_time", record && apiTime(record.end_time), "time", 'step="60" required') + formActiveField(!record || record.is_active);
    }
    var save = dataMode === "demo"
      ? '<button type="submit" class="btn btn-success">Save in Demo Mode</button>'
      : '<button type="submit" class="btn btn-success" disabled>Save disabled</button>';
    return '<form class="crud-form-card" data-crud-form data-crud-resource="' + resource + '" data-crud-id="' + (record ? esc(record.id) : "") + '" novalidate><div class="d-flex justify-content-between align-items-center"><h3>' + title +
      '</h3><span class="badge-soft ' + (dataMode === "demo" ? "" : "warning") + '">' + (dataMode === "demo" ? "Demo only" : "API read-only") + '</span></div><div class="crud-grid">' + fields +
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
      if (!values.slot_date || !values.start_time || !values.end_time || values.start_time.slice(0, 5) >= values.end_time.slice(0, 5)) return { field: "slot_date", message: "Choose a date and ensure start time is earlier than end time." };
      var collision = demoCourtData.slots.find(function (slot) {
        if (String(slot.id) === String(id) || String(slot.court_id) !== String(values.court_id) || slot.slot_date !== values.slot_date) return false;
        var start = values.start_time.slice(0, 5);
        var end = values.end_time.slice(0, 5);
        var exact = slot.start_time.slice(0, 5) === start && slot.end_time.slice(0, 5) === end;
        var overlaps = values.is_active && slot.is_active && slot.start_time.slice(0, 5) < end && slot.end_time.slice(0, 5) > start;
        return exact || overlaps;
      });
      if (collision) return { field: "start_time", message: "This time range duplicates or overlaps another slot for the selected court." };
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
      values.court_id = Number(values.court_id);
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
    document.getElementById("app").innerHTML =
      '<main class="login-page"><section class="login-art">' +
      '<div class="login-brand brand p-0"><span class="brand-mark"><i class="bi bi-trophy"></i></span><span>Courtbook<small>Sports Court Booking</small></span></div>' +
      '<div class="login-message"><p class="eyebrow">Management workspace</p><h1>Run your courts.<br>Keep the game moving.</h1><p>A simple workspace for venue operations, schedules, bookings and check-ins.</p></div>' +
      '<div class="login-art-foot">Sports Court Booking · Management</div></section>' +
      '<section class="login-form-side"><form class="login-card" id="login-form"><p class="eyebrow">Welcome back</p><h2>Sign in to your account</h2><p>Enter your details to open the management dashboard.</p>' +
      '<label class="form-label" for="login-email">Email address</label><input class="form-control" id="login-email" type="email" placeholder="name@example.com" required>' +
      '<label class="form-label" for="login-password">Password</label><input class="form-control" id="login-password" type="password" placeholder="Enter your password" required>' +
      '<label class="form-label" for="login-role">Workspace</label><select class="form-select" id="login-role"><option value="owner">Court Owner</option><option value="admin">Administrator</option></select>' +
      '<button class="btn btn-success w-100" type="submit">Sign in <i class="bi bi-arrow-right ms-1"></i></button>' +
      '<p class="login-demo">Demo prototype · Any email and password opens the selected workspace.</p><div class="login-footnote">Access is provided by your project administrator.</div></form></section></main>';
    document.getElementById("login-form").addEventListener("submit", function (event) {
      event.preventDefault();
      location.hash = document.getElementById("login-role").value === "admin" ? "/admin-dashboard" : "/dashboard";
    });
  }
  function renderShell(content, admin, active) {
    var nav = admin ? adminNav : ownerNav;
    var name = admin ? "Admin User" : "Nguyễn Văn A";
    document.title = info[active][1] + " | Courtbook";
    document.getElementById("app").innerHTML =
      '<div class="app-shell"><aside class="sidebar" id="sidebar"><a class="brand text-decoration-none" href="' + routeLink(admin ? "admin-dashboard" : "dashboard") + '">' +
      '<span class="brand-mark"><i class="bi bi-trophy"></i></span><span>Courtbook<small>Management</small></span></a><div class="side-label">' +
      (admin ? "Administration" : "Operations") + '</div><nav class="side-nav">' + navMarkup(nav, active) + '</nav><div class="side-spacer"></div>' +
      '<a class="side-link" href="#/login"><i class="bi bi-box-arrow-left"></i><span>Sign out</span></a><div class="side-user"><span class="avatar">' +
      (admin ? "AU" : "NA") + '</span><span><strong>' + name + "</strong><small>" + (admin ? "Administrator" : "Court Owner") +
      '</small></span></div></aside><button class="mobile-backdrop" id="mobile-backdrop" aria-label="Close navigation"></button>' +
      '<div class="main-column"><header class="topbar"><button class="icon-button mobile-menu" id="menu-toggle" aria-label="Open navigation"><i class="bi bi-list"></i></button>' +
      '<div class="top-user"><span class="avatar">' + (admin ? "AU" : "NA") + '</span><div><strong>' + name + "</strong><small>" +
      (admin ? "Administrator" : "Owner account") + '</small></div></header><main class="page-content">' + content +
      '<footer class="page-footer">Sports Court Booking · Management workspace</footer></main></div></div>';
    document.getElementById("menu-toggle").addEventListener("click", function () { toggleMenu(true); });
    document.getElementById("mobile-backdrop").addEventListener("click", function () { toggleMenu(false); });
  }
  function toggleMenu(open) {
    document.getElementById("sidebar").classList.toggle("open", open);
    document.getElementById("mobile-backdrop").classList.toggle("open", open);
  }
  function heading(active, action) {
    var item = info[active];
    return '<div class="page-heading"><div><p class="eyebrow">' + item[0] + "</p><h1>" + item[1] + "</h1><p>" + item[2] + "</p></div>" + (action || "") + "</div>";
  }
  function actionButton(label, icon, message, outline) {
    return '<button class="btn ' + (outline ? "btn-outline-secondary" : "btn-success") + '" data-toast="' + message + '"><i class="bi ' + icon + ' me-1"></i><span class="desktop-button-text">' + label + "</span></button>";
  }
  function stats(type, values, live) {
    var set = statSets[type] || statSets.dashboard;
    var ownerDemo = live && dataMode === "demo" && ["dashboard", "venues", "schedule"].indexOf(currentRoute()) >= 0;
    return '<div class="stat-grid">' + values.map(function (value, i) {
      return '<article class="stat-card ' + (type === "admin-dashboard" && i === 3 ? "admin-highlight" : "") + '"><div class="stat-top"><span>' +
        esc(set[i][1]) + '</span><span class="stat-icon"><i class="bi ' + set[i][0] + '"></i></span></div><div class="stat-value">' + esc(value) +
        '</div><div class="stat-note">' + (ownerDemo ? "Demo Mode sample" : (live ? 'Court Service - live count' : 'Demo data')) + '</div></article>';
    }).join("") + "</div>";
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
      }).join("") + '<td class="text-end"><button class="icon-button border-0" data-toast="This is a static demo action." aria-label="More actions"><i class="bi bi-three-dots"></i></button></td></tr>';
    }).join("");
    return '<div class="table-wrap"><table class="table"><thead><tr>' + header + "<th></th></tr></thead><tbody>" + body + "</tbody></table></div>";
  }
  function panel(title, body, subtitle, action) {
    return '<section class="panel-card"><div class="panel-head"><div><h2>' + title + "</h2>" + (subtitle ? "<p>" + subtitle + "</p>" : "") + "</div>" + (action || "") + "</div>" + body + "</section>";
  }
  function bookingRows(admin) { return admin ? data.adminBookings : data.ownerBookings; }
  function recentBookings(admin) {
    var headers = admin ? ["Booking ID", "Customer", "Venue", "Court / time", "Amount", "Status"] : ["Booking ID", "Customer", "Court / time", "Start time", "Amount", "Status"];
    return panel("Recent bookings", table(headers, bookingRows(admin).slice(0, 4)), "The latest activity across your venues");
  }
  function quickActions(admin) {
    var items = admin ? [
      ["bi-person-plus", "Review new owner", "3 accounts waiting", "Review"],
      ["bi-building-add", "Venue applications", "2 venues to review", "Open registry"],
      ["bi-clipboard-data", "View system activity", "Updated moments ago", "View activity"]
    ] : [
      ["bi-plus-circle", "Add a venue", "Set up a new location", "Start setup"],
      ["bi-calendar-plus", "Manage schedule", "Update court availability", "Open schedule"],
      ["bi-qr-code-scan", "Check in a booking", "Scan customer QR at the desk", "Open check-in"]
    ];
    var body = '<div class="panel-body quick-list">' + items.map(function (item) {
      return '<div class="quick-item"><span class="quick-icon"><i class="bi ' + item[0] + '"></i></span><span class="flex-grow-1"><strong>' +
        item[1] + "</strong><small>" + item[2] + '</small></span><button class="btn btn-sm btn-outline-secondary" data-toast="Demo action: ' + item[3] + '.">' + item[3] + "</button></div>";
    }).join("") + "</div>";
    return panel("Quick actions", body);
  }
  function dashboard(active) {
    var resources = currentResources(active !== "admin-dashboard");
    var sports = resources.sports;
    var venues = resources.venues;
    var courts = resources.courts;
    var slots = resources.slots;
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
    else if (!venues.data.length) venueBody = '<div class="panel-body text-secondary">No venues returned by Court Service.</div>';
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
      '<p class="text-secondary small">' + (dataMode === "demo" && active !== "admin-dashboard" ? "Demo sample counts are stored only in browser memory. " : "Counts are from the public Court Service catalogue and are not scoped to the demo Owner account. ") + 'Active slots are administrative records, not booking availability.</p>' +
      (anyError ? (gatewayError ? resourceError("Court Service data", "Failed to fetch") : resourceError("some Court Service data", "One or more lists could not be loaded.")) : "") +
      '<div class="content-grid">' + panel("Venue catalogue", venueBody, dataMode === "demo" && active !== "admin-dashboard" ? "Demo Mode sample" : "Live data from Court Service") +
      panel("Court data", '<div class="panel-body"><p class="mb-2">Sports: ' + (sports.status === "loaded" ? sports.data.length : "?") + '</p><p class="mb-2">Venues: ' + (venues.status === "loaded" ? venues.data.length : "?") + '</p><p class="mb-2">Courts: ' + (courts.status === "loaded" ? courts.data.length : "?") + '</p><p class="mb-0">Active time slots: ' + activeSlots + '</p></div>', "No Booking or revenue data is connected") +
      '</div><div class="mt-3 d-flex gap-2"><a class="btn btn-outline-secondary btn-sm" href="#/venues">Open venues and courts</a><a class="btn btn-outline-secondary btn-sm" href="#/schedule">Open schedule</a></div>';
  }
  function bookingPage(active, admin) {
    if (admin) {
      var adminRows = bookingRows(true);
      return heading(active, actionButton("Export bookings", "bi-download", "Sample booking list exported.", true)) + demoNotice("Booking Service is not connected. Rows and totals below are Demo data.") +
        stats("bookings", ["142", "???38.45M", "126", "16"]) + panel("All bookings", table(["Booking ID", "Customer", "Venue", "Court", "Start time", "Amount", "Status"], adminRows), "Admin sample screen");
    }
    if (dataMode !== "demo") {
      return heading(active) + bookingModeNotice() + panel("Owner bookings", '<div class="panel-body text-secondary">Booking API is waiting for S1. No booking request has been sent.</div>', "No live or mock bookings are shown in API Mode");
    }
    var filtered = filteredDemoBookings();
    var body = '<div class="toolbar"><input class="form-control" type="search" data-booking-search value="' + esc(bookingSearch) + '" placeholder="Search booking ID or customer" aria-label="Search booking ID or customer">' +
      '<input class="form-control" type="date" data-booking-date value="' + esc(bookingDate) + '" aria-label="Filter booking date"><select class="form-select" data-booking-status aria-label="Filter booking status"><option value="">All statuses</option>' +
      ["PENDING", "CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "EXPIRED"].map(function (status) { return '<option value="' + status + '" ' + (bookingStatus === status ? "selected" : "") + '>' + status + '</option>'; }).join("") +
      '</select><button class="btn btn-outline-secondary" data-booking-clear>Clear filters</button></div><div class="table-wrap"><table class="table"><thead><tr><th>Booking ID</th><th>Customer</th><th>Venue</th><th>Court</th><th>Date</th><th>Time</th><th>Total Amount</th><th>Status</th><th>Actions</th></tr></thead><tbody id="owner-booking-rows" aria-live="polite">' +
      bookingRowsMarkup(filtered) + '</tbody></table></div><div class="table-foot" data-booking-count>Showing ' + filtered.length + ' of ' + demoBookings.length + ' Demo bookings - newest first</div>';
    return heading(active) + bookingModeNotice() + demoNotice("Sample booking information is fictional and remains in browser memory only.") + panel("Owner bookings", body, "Filter bookings and open a booking for details");
  }
  function filteredDemoBookings() {
    var query = bookingSearch.trim().toLowerCase();
    return demoBookings.slice().sort(function (a, b) { return b.created_at.localeCompare(a.created_at); }).filter(function (booking) {
      return (!query || booking.id.toLowerCase().indexOf(query) >= 0 || booking.customer.name.toLowerCase().indexOf(query) >= 0) &&
        (!bookingDate || booking.date === bookingDate) && (!bookingStatus || booking.status === bookingStatus);
    });
  }
  function bookingRowsMarkup(bookings) {
    if (!bookings.length) return '<tr><td colspan="9" class="text-secondary">No bookings match these filters.</td></tr>';
    return bookings.map(function (booking) {
      return '<tr><td class="table-primary-text">' + esc(booking.id) + '</td><td>' + esc(booking.customer.name) + '</td><td>' + esc(booking.venue) + '</td><td>' + esc(booking.court) + '</td><td>' + apiDate(booking.date) + '</td><td>' + esc(booking.start_time + " - " + booking.end_time) + '</td><td>' + esc(formatBookingAmount(booking.total_amount)) + '</td><td>' + statusBadge(booking.status) + '</td><td class="table-actions"><button class="btn btn-sm btn-outline-secondary" data-booking-detail="' + esc(booking.id) + '">Details</button>' +
        (booking.status === "CHECKED_IN" ? ' <button class="btn btn-sm btn-success" data-booking-complete="' + esc(booking.id) + '">Complete Booking</button>' : "") + '</td></tr>';
    }).join("");
  }
  function applyBookingFilters() {
    var rows = document.getElementById("owner-booking-rows");
    if (!rows) return;
    bookingSearch = (document.querySelector("[data-booking-search]") || {}).value || "";
    bookingDate = (document.querySelector("[data-booking-date]") || {}).value || "";
    bookingStatus = (document.querySelector("[data-booking-status]") || {}).value || "";
    var filtered = filteredDemoBookings();
    rows.innerHTML = bookingRowsMarkup(filtered);
    var count = document.querySelector("[data-booking-count]");
    if (count) count.textContent = "Showing " + filtered.length + " of " + demoBookings.length + " Demo bookings - newest first";
  }
  function bookingModeNotice() {
    return '<div class="alert alert-warning py-2 small" role="status"><strong>' + (dataMode === "demo" ? "Demo Mode:" : "API Mode:") + '</strong> ' +
      (dataMode === "demo" ? "Booking data below is mock data and is never sent to Booking Service." : "Owner Booking API contract and JWT integration are pending S1; this screen does not call an unconfirmed endpoint.") + '</div>';
  }
  function formatBookingAmount(value) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(value);
  }
  function statusBadge(status) {
    var styles = { PENDING: "warning", CONFIRMED: "", CHECKED_IN: "", COMPLETED: "", CANCELLED: "danger", EXPIRED: "danger" };
    return '<span class="badge-soft ' + (styles[status] || "neutral") + '">' + esc(status) + '</span>';
  }
  function bookingDetail(booking) {
    var customerRows = [["Name", booking.customer.name]];
    if (booking.customer.email) customerRows.push(["Email", booking.customer.email]);
    if (booking.customer.phone) customerRows.push(["Phone", booking.customer.phone]);
    var bookingRows = [["Venue", booking.venue], ["Court", booking.court], ["Date", apiDate(booking.date)], ["Time", booking.start_time + " - " + booking.end_time], ["Total amount", formatBookingAmount(booking.total_amount)]];
    var statusRows = [];
    if (booking.payment_status) statusRows.push(["Payment", booking.payment_status]);
    if (booking.checkin_status) statusRows.push(["QR check-in", booking.checkin_status]);
    function detailSection(title, rows) {
      return '<section class="booking-detail-section"><h3>' + title + '</h3><div class="booking-detail-grid">' + rows.map(function (row) {
        return '<div class="detail-row"><span>' + esc(row[0]) + '</span><strong>' + esc(row[1]) + '</strong></div>';
      }).join("") + '</div></section>';
    }
    var host = document.getElementById("booking-detail-modal-host");
    if (!host) { host = document.createElement("div"); host.id = "booking-detail-modal-host"; document.body.appendChild(host); }
    host.innerHTML = '<div class="modal fade" id="booking-detail-modal" tabindex="-1" aria-labelledby="booking-detail-title" aria-hidden="true"><div class="modal-dialog modal-dialog-centered modal-dialog-scrollable booking-detail-modal"><div class="modal-content"><div class="modal-header align-items-start"><div><p class="eyebrow mb-1">Booking details</p><h2 class="modal-title fs-6" id="booking-detail-title">' + esc(booking.id) + '</h2></div><div class="d-flex align-items-center gap-2">' + statusBadge(booking.status) + '<button type="button" class="btn-close ms-2" data-modal-close aria-label="Close"></button></div></div><div class="modal-body">' + detailSection("Customer", customerRows) + detailSection("Court and booking", bookingRows) + (statusRows.length ? detailSection("Payment and check-in", statusRows) : "") + '</div><div class="modal-footer">' + (booking.status === "CHECKED_IN" && dataMode === "demo" ? '<button type="button" class="btn btn-success" data-booking-complete="' + esc(booking.id) + '">Complete Booking</button>' : "") + '</div></div></div></div>';
    var modal = document.getElementById("booking-detail-modal");
    var completeButton = modal.querySelector("[data-booking-complete]");
    if (completeButton) completeButton.addEventListener("click", function () { completeDemoBooking(booking.id); });
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
    if (dataMode !== "demo") { toast("Booking API and JWT are pending. No request was sent."); return; }
    if (!window.confirm("Complete booking " + booking.id + "?")) return;
    var modal = document.getElementById("booking-detail-modal");
    if (modal) closeManagedModal(modal);
    booking.status = "COMPLETED";
    render();
    toast("Demo booking completed. No API request was sent.");
  }
  function venuePage(active, admin) {
    var editable = !admin;
    var resources = currentResources(editable);
    var venues = resources.venues;
    var courts = resources.courts;
    var sports = resources.sports;
    var venueCards = venues.data.map(function (venue) {
      var linkedCourts = courts.status === "loaded" ? courts.data.filter(function (court) { return court.venue_id === venue.id; }) : [];
      var sportNames = [];
      linkedCourts.forEach(function (court) {
        var sport = sports.data.find(function (item) { return item.id === court.sport_id; });
        if (sport && sportNames.indexOf(sport.name) < 0) sportNames.push(sport.name);
      });
      var ownerLabel = dataMode === "demo" && editable ? "Demo session" : (venue.owner_id ? "Owner #" + venue.owner_id : "Owner unavailable");
      var actions = detailButton("venues", venue.id, "View");
      if (editable) actions += '<div class="crud-actions">' + crudOpenButton("venues", venue.id, "Edit") + crudDeleteButton("venues", venue.id) + "</div>";
      return '<article class="venue-card" data-venue-card data-search="' + esc((venue.name + " " + venue.address).toLowerCase()) + '" data-sport-ids="' + esc(linkedCourts.map(function (court) { return "|" + court.sport_id + "|"; }).join("")) + '" data-active="' + String(!!venue.is_active) + '"><div class="venue-cover"><span class="venue-cover-icon"><i class="bi bi-building"></i></span>' + courtStatus(venue.is_active) + '</div><div class="venue-body"><h3>' +
        esc(venue.name) + '</h3><p><i class="bi bi-geo-alt me-1"></i>' + esc(venue.address) + '</p><div class="venue-meta"><span><strong>' + linkedCourts.length + '</strong> courts</span><span>' + esc(sportNames.join(", ") || "No linked sports") + '</span></div><div class="detail-row"><span>Owner</span><strong>' + esc(ownerLabel) + '</strong></div><div class="d-flex justify-content-between align-items-center gap-2 mt-3">' + actions + '</div></div></article>';
    }).join("");
    var courtRows = courts.data.map(function (court) {
      var venue = venues.data.find(function (item) { return item.id === court.venue_id; });
      var sport = sports.data.find(function (item) { return item.id === court.sport_id; });
      var searchText = [court.name, venue && venue.name, sport && sport.name].filter(Boolean).join(" ").toLowerCase();
      var actions = detailButton("courts", court.id);
      if (editable) actions += '<div class="crud-actions">' + crudOpenButton("courts", court.id, "Edit") + crudDeleteButton("courts", court.id) + "</div>";
      return '<tr data-court-row data-search="' + esc(searchText) + '" data-venue-id="' + esc(court.venue_id) + '" data-sport-id="' + esc(court.sport_id) + '" data-active="' + String(!!court.is_active) + '"><td class="table-primary-text">' + esc(court.name) + '</td><td>' + esc(venue ? venue.name : "Venue #" + court.venue_id) + '</td><td>' + esc(sport ? sport.name : "Sport #" + court.sport_id) + '</td><td>' + formatPriceVnd(court.price_per_hour) + '</td><td>' + courtStatus(court.is_active) + '</td><td class="table-actions">' + actions + '</td></tr>';
    }).join("");
    var sportOptions = sports.data.map(function (sport) { return '<option value="' + esc(sport.id) + '">' + esc(sport.name) + '</option>'; }).join("");
    var venueOptions = venues.data.map(function (venue) { return '<option value="' + esc(venue.id) + '">' + esc(venue.name) + '</option>'; }).join("");
    var sportRows = sports.data.map(function (sport) {
      var actions = detailButton("sports", sport.id) + '<div class="crud-actions">' + crudOpenButton("sports", sport.id, "Edit") + crudDeleteButton("sports", sport.id) + "</div>";
      return '<tr><td class="table-primary-text">' + esc(sport.name) + '</td><td>' + esc(sport.description || "—") + '</td><td>' + courtStatus(sport.is_active) + '</td><td class="table-actions">' + (editable ? actions : detailButton("sports", sport.id)) + '</td></tr>';
    }).join("");
    var sportPanel = editable
      ? panel("Sports", '<div class="toolbar">' + crudOpenButton("sports", null, "Add sport", "btn-success") + '</div>' + crudFormMarkup("sports", resources) + '<div class="table-wrap"><table class="table"><thead><tr><th>Sport</th><th>Description</th><th>Status</th><th>Actions</th></tr></thead><tbody>' + (sportRows || '<tr><td colspan="4" class="text-secondary">No sports. Add one in Demo Mode.</td></tr>') + '</tbody></table></div>', "Sport catalogue")
      : "";
    var sportCount = sports.status === "loaded" ? sports.data.length : "?";
    var venueCount = venues.status === "loaded" ? venues.data.length : "?";
    var courtCount = courts.status === "loaded" ? courts.data.length : "?";
    var activeVenueCount = venues.status === "loaded" ? venues.data.filter(function (venue) { return venue.is_active; }).length : "?";
    var actions = '<div class="page-heading-actions"><button class="btn btn-outline-secondary" data-court-refresh><i class="bi bi-arrow-clockwise me-1"></i>Refresh</button>';
    if (editable) actions += crudOpenButton("venues", null, "Add venue", "btn-success");
    actions += "</div>";
    var stateText = dataMode === "demo" && editable ? "Demo Mode sample" : "Live Court Service data";
    return heading(active, actions) + (editable ? pendingWriteNotice() : "") + stats("court-registry", [sportCount, venueCount, courtCount, activeVenueCount], true) +
      sportPanel +
      '<div class="panel-card mb-3"><div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-venue-search type="search" value="' + esc(venueSearch) + '" placeholder="Search venues" aria-label="Search venues"></div><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-court-search type="search" value="' + esc(courtSearch) + '" placeholder="Search courts" aria-label="Search courts"></div>' +
      '<select class="form-select" data-registry-sport-filter><option value="">All sports</option>' + sportOptions + '</select><select class="form-select" data-registry-active-filter><option value="">All statuses</option><option value="true">Active</option><option value="false">Inactive</option></select><select class="form-select" data-registry-venue-filter><option value="">All venues</option>' + venueOptions + '</select></div>' +
      (editable ? crudFormMarkup("venues", resources) : "") + '<div class="venue-grid" id="venue-grid">' + (venueCards || '<div class="panel-body text-secondary">No venues returned by Court Service.</div>') + '</div><div id="venue-filter-empty" class="alert alert-light mt-2" hidden>No venues match these filters.</div></div>' +
      panel("Courts", '<div class="toolbar">' + (editable ? crudOpenButton("courts", null, "Add court", "btn-success") : "") + '</div>' + (editable ? crudFormMarkup("courts", resources) : "") + '<div class="table-wrap"><table class="table"><thead><tr><th>Court</th><th>Venue</th><th>Sport</th><th>Price per hour</th><th>Status</th><th>Actions</th></tr></thead><tbody>' + (courtRows || '<tr><td colspan="6" class="text-secondary">No courts returned by Court Service.</td></tr>') + '</tbody></table></div><div id="court-filter-empty" class="alert alert-light m-3" hidden>No courts match these filters.</div>', stateText) +
      '<div id="registry-court-error">' + (sports.status === "error" ? resourceError("sports", sports.error) : "") + '</div>';
  }
  function schedulePage() {
    var resources = currentResources(true);
    var courts = resources.courts;
    var venues = resources.venues;
    var slotsState = dataMode === "demo" ? resources.slots : scheduleState;
    var rows = "";
    var statusBlock = "";
    if (slotsState.status === "loading" || slotsState.status === "idle") statusBlock = '<div class="panel-body">Loading time slots...</div>';
    else if (slotsState.status === "error") statusBlock = '<div class="panel-body">' + resourceError("time slots", slotsState.error) + "</div>";
    else {
      var visibleSlots = slotsState.data.filter(function (slot) {
        if (dataMode === "demo" && scheduleFilters.date && slot.slot_date !== scheduleFilters.date) return false;
        if (dataMode === "demo" && scheduleFilters.courtId && String(slot.court_id) !== String(scheduleFilters.courtId)) return false;
        if (!scheduleFilters.venueId) return true;
        var court = courts.data.find(function (item) { return item.id === slot.court_id; });
        return court && String(court.venue_id) === String(scheduleFilters.venueId);
      });
      if (!visibleSlots.length) statusBlock = '<div class="panel-body text-secondary">No time slots match this filter. The active flag does not indicate booking availability.</div>';
      else {
        rows = visibleSlots.map(function (slot) {
          var court = courts.data.find(function (item) { return item.id === slot.court_id; });
          var venue = court && venues.data.find(function (item) { return item.id === court.venue_id; });
          var sport = court && resources.sports.data.find(function (item) { return item.id === court.sport_id; });
          var actions = detailButton("time-slots", slot.id);
          if (dataMode === "demo") actions += '<div class="crud-actions">' + crudOpenButton("slots", slot.id, "Edit") + crudDeleteButton("slots", slot.id) + "</div>";
          else actions += '<div class="crud-actions">' + crudOpenButton("slots", slot.id, "Edit") + crudDeleteButton("slots", slot.id) + "</div>";
          return '<tr><td>' + apiDate(slot.slot_date) + '</td><td>' + esc(venue ? venue.name : (court ? "Venue #" + court.venue_id : "Court #" + slot.court_id)) + '</td><td>' + esc(court ? court.name : "Court #" + slot.court_id) + '</td><td>' + esc(sport ? sport.name : "?") + '</td><td>' + apiTime(slot.start_time) + ' - ' + apiTime(slot.end_time) + '</td><td>' + courtStatus(slot.is_active) + '</td><td class="table-actions">' + actions + '</td></tr>';
        }).join("");
        statusBlock = '<div class="table-wrap"><table class="table"><thead><tr><th>Date</th><th>Venue</th><th>Court</th><th>Sport</th><th>Time</th><th>Status</th><th>Actions</th></tr></thead><tbody>' + rows + '</tbody></table></div><div class="table-foot">Active means the slot record is enabled; booking availability is not provided by this API.</div>';
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
    var addButton = crudOpenButton("slots", null, "Add time slot", "btn-success");
    return relationErrors + heading("schedule", addButton) + pendingWriteNotice() +
      stats("court-overview", [resources.sports.status === "loaded" ? resources.sports.data.length : "?", venues.status === "loaded" ? venues.data.length : "?", courts.status === "loaded" ? courts.data.length : "?", activeSlots], true) +
      panel("Court schedule", '<div class="toolbar"><label class="small" for="schedule-date-filter">Date</label><input id="schedule-date-filter" class="form-control" type="date" data-schedule-date value="' + esc(scheduleFilters.date) + '"><select class="form-select" data-schedule-court><option value="">All courts</option>' + courtOptions + '</select><select class="form-select" data-schedule-venue><option value="">All venues</option>' + venueOptions + '</select><button class="btn btn-success" data-schedule-apply>Apply filters</button><button class="btn btn-outline-secondary" data-schedule-retry>Refresh</button></div>' + crudFormMarkup("slots", resources) + statusBlock, dataMode === "demo" ? "Demo Mode schedule; edits stay in browser memory" : "Time slots from Court Service - no booked/available state") +
      '<p class="small text-secondary mt-2">Time is displayed in local wall-clock format from the API. No timezone conversion is applied.</p>';
  }
  function checkinPage(active, admin) {
    if (admin) {
      var adminRows = data.checkins;
      return heading(active) + demoNotice("Admin check-in management is not part of this iteration.") + panel("Recent check-ins", table(["Check-in ID", "Booking", "Customer", "Venue / court", "Check-in time", "Status"], adminRows));
    }
    var demo = dataMode === "demo";
    var statusLabel = { idle: "IDLE", loading: "STARTING", scanning: "SCANNING", stopping: "STOPPING", success: "SUCCESS", error: "ERROR" }[scannerState] || "IDLE";
    var cameraFrameClass = ["idle", "success", "error"].indexOf(scannerState) >= 0 && !scannerInstance ? "qr-camera-frame--idle" : "qr-camera-frame--active";
    var result = scanResult ? '<div class="alert ' + (scanResult.ok ? "alert-success" : "alert-danger") + '" role="status"><strong>' + esc(scanResult.title) + '</strong><p class="mb-1 mt-2">' + esc(scanResult.message) + '</p>' +
      (scanResult.booking ? '<div class="small">' + esc(scanResult.booking.id + " | " + scanResult.booking.court + " | " + scanResult.booking.date + " " + scanResult.booking.start_time + " - " + scanResult.booking.end_time) + '</div>' : "") + '</div>' : '<p class="text-secondary small" data-scan-result>No QR result yet.</p>';
    var controls = '<div class="qr-camera-controls"><button class="btn btn-success" data-scanner-start ' + (["loading", "scanning", "stopping"].indexOf(scannerState) >= 0 || !!scannerInstance && !qrScanner ? "disabled" : "") + '>Start Camera</button><button class="btn btn-outline-secondary" data-scanner-stop ' + (["loading", "scanning", "stopping"].indexOf(scannerState) < 0 && !scannerInstance && !qrScanner ? "disabled" : "") + '>Stop Camera</button></div>';
    var cameraPanel = '<div class="scanner-frame qr-camera-frame ' + cameraFrameClass + '"><div id="qr-reader" aria-label="Camera preview"></div>' + (scannerState === "idle" ? '<div class="qr-camera-placeholder"><i class="bi bi-qr-code-scan"></i><strong>Camera preview</strong><small>Start the camera when you are ready to scan.</small></div>' : "") + '</div><div class="qr-scanner-footer"><div class="qr-scanner-toolbar"><div class="qr-scanner-status qr-scanner-status--' + scannerState + '" role="status" data-scanner-status>' + statusLabel + '</div>' + controls + '</div><div class="qr-scanner-result" data-scanner-result-host>' + result + '</div></div>';
    var notice = demo ? demoNotice("Demo Only: scan one of the QR tokens from this page or enter it manually below. No real booking token is shown or accepted.") : bookingModeNotice();
    var manual = demo ? '<div class="panel-body"><label class="form-label" for="demo-qr-token">Demo QR token input</label><div class="input-group"><input class="form-control" id="demo-qr-token" autocomplete="off" placeholder="Enter a Demo Only QR token"><button class="btn btn-outline-secondary" data-demo-qr-submit>Check token</button></div><small class="text-secondary">Manual input is for Demo Mode testing only.</small></div>' : '<div class="panel-body text-secondary">Booking Check-in API contract and JWT are pending S1. API Mode does not process scanned tokens or change booking status.</div>';
    var examples = demo ? '<div class="panel-body"><p class="small text-secondary mb-2">Demo Only test tokens</p><div class="qr-demo-token-list">' + demoBookings.map(function (booking) { return '<div class="qr-demo-token"><span><small>' + esc(booking.status) + '</small><br><code>' + esc(booking.qr_token) + '</code></span><button class="btn btn-sm btn-outline-secondary" type="button" data-copy-qr="' + esc(booking.qr_token) + '">Copy</button></div>'; }).join("") + '<div class="qr-demo-token"><span><small>INVALID</small><br><code>demo-qr-invalid</code></span><button class="btn btn-sm btn-outline-secondary" type="button" data-copy-qr="demo-qr-invalid">Copy</button></div></div></div>' : '<div class="panel-body text-secondary">No demo tokens are shown in API Mode.</div>';
    return heading(active) + notice + '<div class="scanner-layout mb-3">' + panel("QR Check-in", cameraPanel, "Camera access starts only after you press Start Camera") + panel("Check-in result", manual + examples, demo ? "Demo Only" : "API integration pending") + '</div>';
  }
  function checkDemoQr(token) {
    if (dataMode !== "demo") {
      setScanResult(false, "API unavailable", "Booking Check-in API is pending S1. No request was sent.");
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
    scannerState = ok ? "success" : "error";
    updateScannerResult();
    updateScannerState(scannerState.toUpperCase());
  }
  function updateScannerResult() {
    var host = document.querySelector("[data-scanner-result-host]");
    if (!host) return;
    if (!scanResult) { host.innerHTML = '<p class="text-secondary small" data-scan-result>No QR result yet.</p>'; return; }
    host.innerHTML = '<div class="alert ' + (scanResult.ok ? "alert-success" : "alert-danger") + '" role="status"><strong>' + esc(scanResult.title) + '</strong><p class="mb-1 mt-2">' + esc(scanResult.message) + '</p>' + (scanResult.booking ? '<div class="small">' + esc(scanResult.booking.id + " | " + scanResult.booking.court + " | " + scanResult.booking.date + " " + scanResult.booking.start_time + " - " + scanResult.booking.end_time) + '</div>' : "") + '</div>';
  }
  function updateScannerState(label) {
    var status = document.querySelector("[data-scanner-status]");
    if (status) {
      status.textContent = label || scannerState.toUpperCase();
      status.className = "qr-scanner-status qr-scanner-status--" + scannerState;
    }
    var start = document.querySelector("[data-scanner-start]");
    var stop = document.querySelector("[data-scanner-stop]");
    if (start) start.disabled = ["loading", "scanning", "stopping"].indexOf(scannerState) >= 0 || (!!scannerInstance && !qrScanner);
    if (stop) stop.disabled = ["loading", "scanning", "stopping"].indexOf(scannerState) < 0 && !scannerInstance && !qrScanner;
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
  function startQrScanner() {
    if (scannerStarting || qrScanner || scannerInstance || scannerStopPromise) return;
    if (dataMode !== "demo") { scannerState = "error"; scanResult = { ok: false, title: "API Mode", message: "Booking Check-in API is pending S1. Scanning is disabled and no request was sent.", booking: null }; updateScannerState("ERROR"); updateScannerResult(); return; }
    if (!window.Html5Qrcode) { scannerState = "error"; scanResult = { ok: false, title: "Scanner library unavailable", message: window.Html5QrcodeLoadError || "html5-qrcode is still loading or could not be loaded. Check your internet/CDN access, then reload this page.", booking: null }; updateScannerState("ERROR"); updateScannerResult(); return; }
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
          if (scannerState !== "scanning") return;
          var now = Date.now();
          if (scanProcessing || (decodedText === lastScannedText && now - lastScanAt < 2500)) return;
          scanProcessing = true; lastScannedText = decodedText; lastScanAt = now;
          stopQrScanner().then(function (stopped) { scanProcessing = false; if (stopped) checkDemoQr(decodedText); });
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
        return typeof activeScanner.clear === "function" ? activeScanner.clear() : undefined;
      }).then(function () {
        if (scannerInstance === activeScanner) scannerInstance = null;
        if (qrScanner === activeScanner) qrScanner = null;
        scannerStarting = false; scannerState = "error"; scanResult = { ok: false, title: "Camera error", message: message, booking: null }; updateScannerState("ERROR"); updateScannerResult();
      }).catch(function (cleanupError) {
        scannerStarting = false; scannerState = "error"; scanResult = { ok: false, title: "Camera cleanup error", message: message + " Camera cleanup failed: " + (cleanupError && cleanupError.message ? cleanupError.message : "unknown error") + ". Press Stop Camera to retry cleanup.", booking: null }; updateScannerState("ERROR"); updateScannerResult();
      });
    }).finally(function () { scannerStartPromise = null; });
  }
  function stopQrScanner() {
    if (scannerStopPromise) return scannerStopPromise;
    var current = qrScanner || scannerInstance;
    if (!current) { scannerStarting = false; return Promise.resolve(true); }
    ++scannerEpoch; scannerState = "stopping"; updateScannerState("STOPPING");
    scannerStopPromise = Promise.resolve().then(function () {
      return scannerStartPromise ? scannerStartPromise.then(function () { return true; }, function () { return false; }) : true;
    }).then(function (started) {
      if (!started) return false;
      if (current.isScanning || current.stateManager && current.stateManager.getState && current.stateManager.getState() === 2) return Promise.resolve(current.stop()).then(function () { return true; });
      return true;
    }).then(function (started) {
      if (current.isScanning) throw new Error("Scanner did not stop; camera cleanup was not attempted.");
      return typeof current.clear === "function" ? current.clear() : undefined;
    }).then(function () {
      scannerInstance = null; qrScanner = null; scannerStarting = false; scannerState = "idle"; updateScannerState("IDLE"); return true;
    }).catch(function (error) {
      scannerState = "error"; scanResult = { ok: false, title: "Camera stop error", message: error && error.message ? error.message : "Could not stop the camera safely. Retry Stop Camera.", booking: null }; updateScannerState("ERROR"); updateScannerResult(); return false;
    }).finally(function () { scannerStopPromise = null; });
    return scannerStopPromise;
  }
  function revenuePage() {
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
    return heading("revenue", actionButton("Download report", "bi-download", "Sample revenue report downloaded.", true)) + demoNotice("Payment and Revenue APIs are not connected. All values below are Demo data.") +
      stats("revenue", ["₫12.45M", "₫4.68M", "₫7.77M", "₫1.24M"]) + '<div class="content-grid">' +
      panel("Revenue overview", chart, "Monthly performance") + panel("Revenue by sport", breakdown, "This month") +
      '</div><p class="text-secondary mt-3" style="font-size:10px"><i class="bi bi-info-circle me-1"></i>Revenue figures are mock data for this interface preview.</p>';
  }
  function peoplePage() {
    var rows = data.people.map(function (row) { return [row[1], row[2] + " · " + row[0], row[3], row[4], row[5]]; });
    return heading("people", actionButton("Add account", "bi-person-plus", "Account creation is a UI-only demo.")) + demoNotice("User Service is not connected. Accounts and totals below are Demo data.") +
      stats("people", ["1,248", "1,204", "32", "12"]) +
      panel("Account directory", '<div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-table-search type="search" placeholder="Search name or email"></div><select class="form-select"><option>All roles</option><option>User</option><option>Court Owner</option></select><select class="form-select"><option>All statuses</option><option>Active</option><option>Pending</option><option>Inactive</option></select></div>' +
      table(["Account", "Email", "Role", "Joined", "Status"], rows) + '<div class="table-foot"><span>Showing ' + rows.length + " sample accounts</span>" + actionButton("Export users", "bi-download", "Sample account list exported.", true) + "</div>");
  }
  function profilePage(active, admin) {
    var name = admin ? "Admin User" : "Nguyễn Văn A";
    var email = admin ? "admin@sportbooking.vn" : "owner@sportbooking.vn";
    return heading(active) + demoNotice("Profile API is not connected. Profile details are Demo data.") + '<div class="profile-layout"><section class="profile-card profile-summary"><span class="avatar">' + (admin ? "AU" : "NA") +
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
    if (active === "schedule") return schedulePage();
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
    document.querySelectorAll(".table tbody tr").forEach(function (row) {
      row.hidden = row.innerText.toLowerCase().indexOf(search.toLowerCase()) < 0 ||
        (status && row.innerText.toLowerCase().indexOf(status.toLowerCase()) < 0);
    });
  }
  function applyRegistryFilters() {
    venueSearch = (document.querySelector("[data-venue-search]") || {}).value || "";
    courtSearch = (document.querySelector("[data-court-search]") || {}).value || "";
    var sportId = (document.querySelector("[data-registry-sport-filter]") || {}).value || "";
    var active = (document.querySelector("[data-registry-active-filter]") || {}).value || "";
    var venueId = (document.querySelector("[data-registry-venue-filter]") || {}).value || "";
    var venueCards = Array.prototype.slice.call(document.querySelectorAll("[data-venue-card]"));
    var courtRows = Array.prototype.slice.call(document.querySelectorAll("[data-court-row]"));
    var visibleVenues = 0;
    var visibleCourts = 0;
    venueCards.forEach(function (card) {
      var show = card.dataset.search.indexOf(venueSearch.toLowerCase()) >= 0 &&
        (!sportId || card.dataset.sportIds.indexOf("|" + sportId + "|") >= 0) &&
        (!active || card.dataset.active === active);
      card.hidden = !show;
      if (show) visibleVenues += 1;
    });
    courtRows.forEach(function (row) {
      var show = row.dataset.search.indexOf(courtSearch.toLowerCase()) >= 0 &&
        (!sportId || row.dataset.sportId === sportId) &&
        (!active || row.dataset.active === active) &&
        (!venueId || row.dataset.venueId === venueId);
      row.hidden = !show;
      if (show) visibleCourts += 1;
    });
    var venueEmpty = document.getElementById("venue-filter-empty");
    var courtEmpty = document.getElementById("court-filter-empty");
    if (venueEmpty) venueEmpty.hidden = venueCards.length === 0 || visibleVenues > 0;
    if (courtEmpty) courtEmpty.hidden = courtRows.length === 0 || visibleCourts > 0;
  }
  function saveDemoRecord(form) {
    var resource = form.dataset.crudResource;
    var id = form.dataset.crudId || null;
    var values = demoFormValues(form, resource);
    var error = validateDemoForm(resource, values, id);
    if (error) {
      form.querySelectorAll(".field-error").forEach(function (node) { node.textContent = ""; });
      form.querySelectorAll(".is-invalid").forEach(function (node) { node.classList.remove("is-invalid"); });
      var field = form.elements.namedItem(error.field);
      var feedback = form.querySelector('[data-field-error="' + error.field + '"]');
      if (field) field.classList.add("is-invalid");
      if (feedback) feedback.textContent = error.message;
      if (field) field.focus();
      return;
    }
    var records = recordsFor(resource);
    var existing = id ? records.find(function (item) { return String(item.id) === String(id); }) : null;
    if (existing) Object.assign(existing, values);
    else {
      values.id = nextDemoId(records);
      records.push(values);
    }
    crudFormState = null;
    render();
    toast((existing ? "Updated " : "Added ") + ({ sports: "sport", venues: "venue", courts: "court", slots: "time slot" }[resource]) + " in Demo Mode.");
  }
  function deactivateDemoRecord(resource, id) {
    if (dataMode !== "demo") {
      toast("API Mode is read-only until JWT integration. No data was changed.");
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
    var modeSelect = document.getElementById("court-data-mode");
    if (modeSelect) modeSelect.addEventListener("change", function () {
      var nextMode = modeSelect.value;
      if (currentRoute() === "qr-checkin" && (qrScanner || scannerInstance || scannerStarting)) {
        modeSelect.disabled = true;
        stopQrScanner().then(function (stopped) {
          if (stopped) {
            dataMode = nextMode; scannerState = "idle"; scanResult = null; crudFormState = null; render();
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
        if (dataMode !== "demo") {
          toast("API Mode is read-only until JWT integration. No write request was sent.");
          return;
        }
        saveDemoRecord(form);
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
        toast("Write actions are waiting for JWT integration. No data was sent or saved.");
      });
    });
    document.querySelectorAll("[data-court-retry], [data-court-refresh]").forEach(function (el) {
      el.addEventListener("click", function () {
        if (dataMode === "demo") {
          demoCourtData = window.CourtDemoData.create();
          crudFormState = null;
          render();
          toast("Demo sample restored to its starting data.");
        } else loadCourtResources(true);
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
    document.querySelectorAll("[data-table-search], [data-status-filter]").forEach(function (el) {
      el.addEventListener("input", filterRows);
      el.addEventListener("change", filterRows);
    });
    var bookingSearchInput = document.querySelector("[data-booking-search]");
    if (bookingSearchInput) bookingSearchInput.addEventListener("input", applyBookingFilters);
    var bookingDateInput = document.querySelector("[data-booking-date]");
    if (bookingDateInput) bookingDateInput.addEventListener("change", applyBookingFilters);
    var bookingStatusInput = document.querySelector("[data-booking-status]");
    if (bookingStatusInput) bookingStatusInput.addEventListener("change", applyBookingFilters);
    var bookingClear = document.querySelector("[data-booking-clear]");
    if (bookingClear) bookingClear.addEventListener("click", function () {
      bookingSearch = ""; bookingDate = ""; bookingStatus = "";
      if (bookingSearchInput) bookingSearchInput.value = "";
      if (bookingDateInput) bookingDateInput.value = "";
      if (bookingStatusInput) bookingStatusInput.value = "";
      applyBookingFilters();
      if (bookingSearchInput) bookingSearchInput.focus();
    });
    var bookingRowsHost = document.getElementById("owner-booking-rows");
    if (bookingRowsHost) bookingRowsHost.addEventListener("click", function (event) {
      var detailButton = event.target.closest("[data-booking-detail]");
      var completeButton = event.target.closest("[data-booking-complete]");
      if (detailButton) {
        var booking = demoBookings.find(function (item) { return item.id === detailButton.dataset.bookingDetail; });
        if (booking) bookingDetail(booking);
      } else if (completeButton) completeDemoBooking(completeButton.dataset.bookingComplete);
    });
    var scannerStart = document.querySelector("[data-scanner-start]");
    if (scannerStart) scannerStart.addEventListener("click", startQrScanner);
    var scannerStop = document.querySelector("[data-scanner-stop]");
    if (scannerStop) scannerStop.addEventListener("click", function () { stopQrScanner(); });
    var demoQrSubmit = document.querySelector("[data-demo-qr-submit]");
    if (demoQrSubmit) demoQrSubmit.addEventListener("click", function () { checkDemoQr((document.getElementById("demo-qr-token").value || "").trim()); });
    document.querySelectorAll("[data-copy-qr]").forEach(function (el) {
      el.addEventListener("click", function () {
        var token = el.dataset.copyQr;
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(token).then(function () { toast("Demo QR token copied."); }).catch(function () { toast("Copy was blocked; select the token text to copy it."); });
        else toast("Select the Demo token text and copy it manually.");
      });
    });
    document.querySelectorAll("[data-venue-search], [data-court-search]").forEach(function (el) {
      el.addEventListener("input", applyRegistryFilters);
    });
    document.querySelectorAll("[data-registry-sport-filter], [data-registry-active-filter], [data-registry-venue-filter]").forEach(function (el) {
      el.addEventListener("change", applyRegistryFilters);
    });
    var scheduleApply = document.querySelector("[data-schedule-apply]");
    if (scheduleApply) scheduleApply.addEventListener("click", function () {
      scheduleFilters.date = (document.querySelector("[data-schedule-date]") || {}).value || "";
      scheduleFilters.courtId = (document.querySelector("[data-schedule-court]") || {}).value || "";
      scheduleFilters.venueId = (document.querySelector("[data-schedule-venue]") || {}).value || "";
      refreshSchedule();
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
    if (active === "login") { renderLogin(); return; }
    if (active === "qr-checkin" && (scannerStarting || qrScanner || scannerInstance || scannerStopPromise) && document.getElementById("qr-reader")) {
      updateScannerState();
      updateScannerResult();
      return;
    }
    var admin = active.indexOf("admin-") === 0 || active === "people" || active === "checkins";
    if (!info[active]) active = admin ? "admin-dashboard" : "dashboard";
    var content = pageFor(active);
    var ownerCourtScreens = ["dashboard", "venues", "schedule"];
    if (!admin && (ownerCourtScreens.indexOf(active) >= 0 || active === "owner-bookings" || active === "qr-checkin")) content = modeToolbar() + content;
    renderShell(content, admin, active);
    wireActions();
    var courtScreens = ["dashboard", "admin-dashboard", "venues", "admin-venues", "schedule"];
    if (active === "qr-checkin" && dataMode === "demo" && !window.Html5Qrcode) {
      window.addEventListener("load", function () { updateScannerState(); }, { once: true });
    }
    if (dataMode === "api" && courtScreens.indexOf(active) >= 0 && Object.keys(courtResources).every(function (key) { return courtResources[key].status === "idle"; })) {
      loadCourtResources(false);
    }
  }
  var renderedRoute = currentRoute();
  var navigationStopPromise = null;
  window.addEventListener("hashchange", function () {
    var nextRoute = currentRoute();
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
  document.addEventListener("qrscannerloaderror", function () {
    var start = document.querySelector("[data-scanner-start]");
    if (start && currentRoute() === "qr-checkin") { start.disabled = false; start.title = window.Html5QrcodeLoadError; }
  });
  render();
})();
