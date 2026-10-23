(function () {
  "use strict";
  var data = window.BookingMockData;
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
    dashboard: ["Owner dashboard", "Welcome back, Nguyễn Văn A", "Here is what is happening at your venues today."],
    venues: ["Venue management", "Venue & Court", "Manage your sports venues, courts, and availability."],
    schedule: ["Court operations", "Facility Schedule", "Review your court availability for this week."],
    "owner-bookings": ["Owner operations", "Bookings Management", "Track and review reservations across your venues."],
    "qr-checkin": ["Front desk", "QR Check-in Terminal", "Verify a customer booking before check-in."],
    revenue: ["Business overview", "Revenue & Payouts", "Sample revenue summary for your venues."],
    "owner-profile": ["Account settings", "Owner Profile", "Manage the contact details associated with your account."],
    "admin-dashboard": ["System overview", "Admin Dashboard", "A snapshot of the Sports Court Booking platform."],
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
    checkins: [["bi-qr-code", "Check-ins today"], ["bi-shield-check", "Verified"], ["bi-building", "Active venues"], ["bi-exclamation-circle", "Manual reviews"]]
  };

  function currentRoute() {
    return (location.hash.replace(/^#\/?/, "") || "login").toLowerCase();
  }
  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
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
      '<div class="input-group top-search"><span class="input-group-text border-0 bg-transparent text-secondary"><i class="bi bi-search"></i></span><input class="form-control" type="search" placeholder="Search bookings, venues, users..."></div>' +
      '<div class="d-flex align-items-center gap-3"><button class="icon-button" data-toast="You are all caught up." aria-label="Notifications"><i class="bi bi-bell"></i></button>' +
      '<div class="top-user"><span class="avatar">' + (admin ? "AU" : "NA") + '</span><div><strong>' + name + "</strong><small>" +
      (admin ? "Administrator" : "Owner account") + '</small></div></div></div></header><main class="page-content">' + content +
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
  function stats(type, values) {
    var set = statSets[type] || statSets.dashboard;
    return '<div class="stat-grid">' + values.map(function (value, i) {
      return '<article class="stat-card ' + (type === "admin-dashboard" && i === 3 ? "admin-highlight" : "") + '"><div class="stat-top"><span>' +
        set[i][1] + '</span><span class="stat-icon"><i class="bi ' + set[i][0] + '"></i></span></div><div class="stat-value">' + value +
        '</div><div class="stat-note"><span class="trend-up"><i class="bi bi-arrow-up-right"></i> 8.4%</span> vs last month</div></article>';
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
    var admin = active === "admin-dashboard";
    return heading(active, actionButton("Export report", "bi-download", "Your sample report is ready to export.", true)) +
      stats(active, admin ? ["1,248", "32", "856", "₫48.23M"] : ["28", "₫12.45M", "8", "76%"]) +
      '<div class="content-grid">' + recentBookings(admin) + quickActions(admin) + "</div>";
  }
  function bookingPage(active, admin) {
    var rows = bookingRows(admin);
    var heads = admin ? ["Booking ID", "Customer", "Venue", "Court", "Start time", "Amount", "Status"] : ["Booking ID", "Customer", "Court", "Start time", "Amount", "Status"];
    return heading(active, actionButton("Export bookings", "bi-download", "Sample booking list exported.", true)) +
      stats("bookings", admin ? ["142", "₫38.45M", "126", "16"] : ["28", "₫4.68M", "21", "3"]) +
      panel("All bookings", '<div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" type="search" data-table-search placeholder="Search by booking or customer"></div>' +
      '<select class="form-select" data-status-filter><option value="">All statuses</option><option>Confirmed</option><option>Pending</option><option>Checked in</option><option>Completed</option><option>Cancelled</option></select>' +
      '<button class="btn btn-outline-secondary" data-toast="Date range filters are part of the connected version."><i class="bi bi-calendar3 me-1"></i>Date range</button></div>' +
      table(heads, rows) + '<div class="table-foot"><span>Showing ' + rows.length + ' sample bookings</span><nav><ul class="pagination pagination-sm"><li class="page-item active"><a class="page-link" href="#">1</a></li><li class="page-item"><a class="page-link" href="#" data-toast="More sample rows can be added later.">2</a></li></ul></nav></div>');
  }
  function venuePage(active, admin) {
    var cards = data.venues.map(function (venue) {
      return '<article class="venue-card"><div class="venue-cover ' + venue.tone + '"><span class="venue-cover-icon"><i class="bi bi-building"></i></span>' + badge(venue.status) + '</div><div class="venue-body"><h3>' +
        venue.name + '</h3><p><i class="bi bi-geo-alt me-1"></i>' + venue.area + " · " + venue.sport + '</p><div class="venue-meta"><span><strong>' +
        venue.courts + '</strong> courts</span><span><strong>' + venue.slots + '</strong> slots today</span></div><div class="d-flex justify-content-end gap-2 mt-3">' +
        '<button class="btn btn-sm btn-outline-secondary" data-toast="Venue details are sample data.">View</button><button class="btn btn-sm btn-success" data-toast="Venue editing will be connected to the API later.">Edit</button></div></div></article>';
    }).join("");
    return heading(active, actionButton("Add venue", "bi-plus-lg", "Venue creation is a UI-only demo.")) +
      stats(admin ? "admin-venues" : "venues", admin ? ["32", "148", "29", "3"] : ["3", "19", "48", "2"]) +
      '<div class="panel-card mb-3"><div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-venue-search type="search" placeholder="Search venue"></div>' +
      '<select class="form-select"><option>All sports</option><option>Badminton</option><option>Football</option><option>Pickleball</option></select><select class="form-select"><option>All statuses</option><option>Open</option><option>Review</option></select></div></div>' +
      '<div class="venue-grid" id="venue-grid">' + cards + "</div>";
  }
  function schedulePage() {
    var days = ["Court", "Mon 19", "Tue 20", "Wed 21", "Thu 22", "Fri 23", "Sat 24", "Sun 25"];
    var rows = [
      ["Badminton · Court 01", "6 / 10", "8 / 10", "5 / 10", "7 / 10", "9 / 10", "10 / 10", "8 / 10"],
      ["Badminton · Court 02", "7 / 10", "6 / 10", "8 / 10", "4 / 10", "8 / 10", "9 / 10", "7 / 10"],
      ["Football · Field A", "4 / 8", "5 / 8", "6 / 8", "6 / 8", "7 / 8", "8 / 8", "7 / 8"],
      ["Pickleball · Court 03", "3 / 10", "5 / 10", "6 / 10", "5 / 10", "6 / 10", "8 / 10", "6 / 10"]
    ];
    var trs = rows.map(function (row) {
      return '<tr><td class="schedule-time text-start">' + row[0] + "</td>" + row.slice(1).map(function (value, index) {
        var style = value.charAt(0) === "3" || value.charAt(0) === "4" ? "closed" : (index > 3 ? "busy" : "");
        return '<td><span class="slot ' + style + '">' + value + " slots</span></td>";
      }).join("") + "</tr>";
    }).join("");
    var body = '<div class="toolbar"><button class="btn btn-outline-secondary" data-toast="Showing the current sample week."><i class="bi bi-chevron-left"></i></button><button class="btn btn-outline-secondary" data-toast="Showing the current sample week.">Oct 19 – Oct 25, 2026 <i class="bi bi-calendar3 ms-1"></i></button><button class="btn btn-outline-secondary" data-toast="Showing the current sample week."><i class="bi bi-chevron-right"></i></button><span class="flex-grow-1"></span><select class="form-select"><option>All venues</option><option>Green Field Sports Center</option></select></div>' +
      '<div class="table-wrap"><table class="table schedule-table"><thead><tr>' + days.map(function (day) { return "<th>" + day + "</th>"; }).join("") + "</tr></thead><tbody>" + trs + '</tbody></table></div><div class="table-foot"><span><span class="slot me-1">Available</span><span class="slot busy me-1">Busy</span><span class="slot closed">Low availability</span></span>' +
      actionButton("Edit schedule", "bi-pencil", "Schedule editor is a UI-only demo.", true) + "</div>";
    return heading("schedule", actionButton("Add time slot", "bi-plus-lg", "Time-slot creation is a UI-only demo.")) + stats("venues", ["3", "19", "48", "2"]) + panel("Weekly facility schedule", body, "Availability by court · Sample data");
  }
  function checkinPage(active, admin) {
    var rows = admin ? data.checkins : data.checkins.slice(0, 3);
    var heads = ["Check-in ID", "Booking", "Customer", "Venue / court", "Check-in time", "Status"];
    if (admin) return heading(active, actionButton("Export history", "bi-download", "Sample check-in history exported.", true)) +
      stats("checkins", ["64", "62", "18", "2"]) + panel("Check-in history",
        '<div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-table-search type="search" placeholder="Search booking or customer"></div><select class="form-select"><option>All venues</option><option>Green Field</option></select><select class="form-select"><option>Today</option><option>Last 7 days</option></select></div>' + table(heads, rows));
    var scan = '<div class="panel-body"><div class="scanner-frame"><div><i class="bi bi-qr-code-scan"></i><strong>Camera preview</strong><small>QR scanning will be connected in a later iteration.</small></div></div><div class="d-flex gap-2 mt-3"><button class="btn btn-success flex-grow-1" data-toast="Camera scanning is not connected in this prototype."><i class="bi bi-camera me-1"></i>Start scanner</button><button class="btn btn-outline-secondary" data-toast="Choose an image after scanner integration."><i class="bi bi-image"></i></button></div></div>';
    var verify = '<div class="panel-body"><label class="form-label" for="booking-token">Booking code or QR token</label><div class="input-group"><input class="form-control" id="booking-token" placeholder="e.g. BK-2047"><button class="btn btn-success" id="verify-booking">Verify</button></div><p class="text-secondary mt-2 mb-3" style="font-size:10px">Enter a sample booking ID to preview the confirmation state.</p><div id="verify-result" class="scan-result d-none"><i class="bi bi-patch-check-fill"></i><span><strong>Booking found · Ready for check-in</strong><small>Quang Huy · City Arena, Field A · Today at 17:30</small></span></div><div class="profile-divider"></div><div class="detail-row"><span>Venue</span><strong>City Arena</strong></div><div class="detail-row"><span>Check-in window</span><strong>15 min before start</strong></div><div class="detail-row"><span>Last scan</span><strong>Not scanned yet</strong></div></div>';
    return heading(active) + '<div class="scanner-layout mb-3">' + panel("Scan booking QR", scan, "Customer presents their booking QR code") +
      panel("Verify booking manually", verify, "Confirm the booking before admitting a customer") + "</div>" +
      panel("Recent check-ins", table(heads, rows), "Latest check-ins at your venues");
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
    return heading("revenue", actionButton("Download report", "bi-download", "Sample revenue report downloaded.", true)) +
      stats("revenue", ["₫12.45M", "₫4.68M", "₫7.77M", "₫1.24M"]) + '<div class="content-grid">' +
      panel("Revenue overview", chart, "Monthly performance") + panel("Revenue by sport", breakdown, "This month") +
      '</div><p class="text-secondary mt-3" style="font-size:10px"><i class="bi bi-info-circle me-1"></i>Revenue figures are mock data for this interface preview.</p>';
  }
  function peoplePage() {
    var rows = data.people.map(function (row) { return [row[1], row[2] + " · " + row[0], row[3], row[4], row[5]]; });
    return heading("people", actionButton("Add account", "bi-person-plus", "Account creation is a UI-only demo.")) +
      stats("people", ["1,248", "1,204", "32", "12"]) +
      panel("Account directory", '<div class="toolbar"><div class="input-group search-field"><span class="input-group-text bg-white border-end-0"><i class="bi bi-search"></i></span><input class="form-control border-start-0" data-table-search type="search" placeholder="Search name or email"></div><select class="form-select"><option>All roles</option><option>User</option><option>Court Owner</option></select><select class="form-select"><option>All statuses</option><option>Active</option><option>Pending</option><option>Inactive</option></select></div>' +
      table(["Account", "Email", "Role", "Joined", "Status"], rows) + '<div class="table-foot"><span>Showing ' + rows.length + " sample accounts</span>" + actionButton("Export users", "bi-download", "Sample account list exported.", true) + "</div>");
  }
  function profilePage(active, admin) {
    var name = admin ? "Admin User" : "Nguyễn Văn A";
    var email = admin ? "admin@sportbooking.vn" : "owner@sportbooking.vn";
    return heading(active) + '<div class="profile-layout"><section class="profile-card profile-summary"><span class="avatar">' + (admin ? "AU" : "NA") +
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
    node.className = "toast align-items-center border-0";
    node.setAttribute("role", "status");
    node.innerHTML = '<div class="d-flex"><div class="toast-body"><i class="bi bi-info-circle text-success me-2"></i>' + esc(message) + '</div><button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>';
    host.appendChild(node);
    var instance = new bootstrap.Toast(node, { delay: 2600 });
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
  function wireActions() {
    document.querySelectorAll("[data-toast]").forEach(function (el) {
      el.addEventListener("click", function (event) {
        if (el.tagName === "A") event.preventDefault();
        toast(el.dataset.toast);
      });
    });
    document.querySelectorAll("[data-table-search], [data-status-filter]").forEach(function (el) {
      el.addEventListener("input", filterRows);
      el.addEventListener("change", filterRows);
    });
    var venueSearch = document.querySelector("[data-venue-search]");
    if (venueSearch) venueSearch.addEventListener("input", function () {
      var query = venueSearch.value.toLowerCase();
      document.querySelectorAll("#venue-grid .venue-card").forEach(function (card) {
        card.hidden = card.innerText.toLowerCase().indexOf(query) < 0;
      });
    });
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
    var admin = active.indexOf("admin-") === 0 || active === "people" || active === "checkins";
    if (!info[active]) active = admin ? "admin-dashboard" : "dashboard";
    renderShell(pageFor(active), admin, active);
    wireActions();
  }
  window.addEventListener("hashchange", render);
  render();
})();
