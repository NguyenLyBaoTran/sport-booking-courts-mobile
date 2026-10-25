(function (root) {
  "use strict";

  function validParts(year, month, day) {
    if (year < 1 || year > 9999 || month < 1 || month > 12 || day < 1) return false;
    var daysInMonth = [31, (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    return day <= daysInMonth[month - 1];
  }

  function parseDateInput(value) {
    var text = String(value || "").trim();
    var iso = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(text);
    var vietnamese = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text);
    var year, month, day;
    if (iso) {
      year = Number(iso[1]); month = Number(iso[2]); day = Number(iso[3]);
    } else if (vietnamese) {
      day = Number(vietnamese[1]); month = Number(vietnamese[2]); year = Number(vietnamese[3]);
    } else return { valid: false, iso: "" };
    if (!validParts(year, month, day)) return { valid: false, iso: "" };
    return { valid: true, iso: String(year).padStart(4, "0") + "-" + String(month).padStart(2, "0") + "-" + String(day).padStart(2, "0") };
  }

  function parseDateSearch(value) {
    var text = String(value || "").trim();
    var full = parseDateInput(text);
    if (full.valid) return { dateLike: true, valid: true, iso: full.iso };
    if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(text) || /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(text)) {
      return { dateLike: true, valid: false };
    }
    var partial = /^(\d{1,2})\/(\d{1,2})$/.exec(text);
    if (!partial) return null;
    var day = Number(partial[1]);
    var month = Number(partial[2]);
    return { dateLike: true, valid: day >= 1 && day <= 31 && month >= 1 && month <= 12, day: day, month: month };
  }

  function matchesDateSearch(value, slotDate) {
    var search = parseDateSearch(value);
    if (!search) return null;
    if (!search.valid) return false;
    var slot = parseDateInput(slotDate);
    if (!slot.valid) return false;
    if (search.iso) return search.iso === slot.iso;
    var parts = slot.iso.split("-");
    return Number(parts[1]) === search.month && Number(parts[2]) === search.day;
  }

  function courtsForVenue(courts, venueId) {
    return (courts || []).filter(function (court) { return String(court.venue_id) === String(venueId); });
  }

  function matchesDateFilter(filterDate, slotDate) {
    if (!filterDate) return true;
    var filter = parseDateInput(filterDate);
    var slot = parseDateInput(slotDate);
    return filter.valid && slot.valid && filter.iso === slot.iso;
  }

  function formatDateDisplay(value) {
    var parsed = parseDateInput(value);
    if (!parsed.valid) return "";
    var parts = parsed.iso.split("-");
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function selectScheduleDate(filters, value) {
    var parsed = parseDateInput(value);
    if (!parsed.valid) return null;
    return Object.assign({}, filters, { date: parsed.iso });
  }

  function calendarDays(year, month) {
    var firstWeekday = new Date(Date.UTC(year, month, 1)).getUTCDay();
    var mondayOffset = (firstWeekday + 6) % 7;
    return Array.from({ length: 42 }, function (_, index) {
      var day = new Date(Date.UTC(year, month, 1 - mondayOffset + index));
      var dayYear = day.getUTCFullYear();
      var dayMonth = day.getUTCMonth();
      var dayNumber = day.getUTCDate();
      var iso = String(dayYear).padStart(4, "0") + "-" + String(dayMonth + 1).padStart(2, "0") + "-" + String(dayNumber).padStart(2, "0");
      return { iso: iso, day: dayNumber, inMonth: dayYear === year && dayMonth === month };
    });
  }

  function matchesScheduleFilters(slot, related, filters) {
    var searchText = [slot.slot_date, slot.start_time, slot.end_time, related.venueName, related.courtName, related.sportName].filter(Boolean).join(" ").toLowerCase();
    var query = String(filters.search || "").trim().toLowerCase();
    var dateSearch = query ? matchesDateSearch(query, slot.slot_date) : null;
    var searchMatches = !query || (dateSearch === null ? searchText.indexOf(query) >= 0 : dateSearch);
    return searchMatches && matchesDateFilter(filters.date, slot.slot_date) &&
      (!filters.courtId || String(slot.court_id) === String(filters.courtId)) &&
      (!filters.venueId || String(related.venueId) === String(filters.venueId)) &&
      (!filters.status || String(!!slot.is_active) === filters.status);
  }

  function fetchTimeSlotsForCourts(courts, getCollection) {
    return Promise.all((courts || []).map(function (court) {
      return getCollection("/api/v1/time-slots?court_id=" + encodeURIComponent(court.id));
    })).then(function (groups) { return [].concat.apply([], groups); });
  }

  function refreshDemoSchedule(demoData, confirmed, initialSlots) {
    if (!confirmed) return false;
    demoData.slots = initialSlots;
    return true;
  }

  function emptyFilters() {
    return { search: "", date: "", courtId: "", venueId: "", status: "" };
  }

  function hasTimeSlotOverlap(slots, candidate, currentId) {
    return (slots || []).some(function (slot) {
      if (String(slot.id) === String(currentId) || String(slot.court_id) !== String(candidate.court_id) || slot.slot_date !== candidate.slot_date) return false;
      var start = String(candidate.start_time).slice(0, 5);
      var end = String(candidate.end_time).slice(0, 5);
      var exact = String(slot.start_time).slice(0, 5) === start && String(slot.end_time).slice(0, 5) === end;
      var overlaps = candidate.is_active && slot.is_active && String(slot.start_time).slice(0, 5) < end && String(slot.end_time).slice(0, 5) > start;
      return exact || overlaps;
    });
  }

  function businessDateTime(now) {
    var parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
    }).formatToParts(now || new Date());
    var values = {};
    parts.forEach(function (part) { if (part.type !== "literal") values[part.type] = part.value; });
    return values.year + "-" + values.month + "-" + values.day + "T" + values.hour + ":" + values.minute + ":" + values.second;
  }

  function validateFutureStart(candidate, existing, now) {
    var date = parseDateInput(candidate.slot_date);
    if (!date.valid) return "Enter a valid date.";
    var startTime = String(candidate.start_time || "").slice(0, 8);
    if (!/^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$/.test(startTime)) return "Enter a valid start time.";
    if (existing) {
      var previousDate = parseDateInput(existing.slot_date);
      var previousStart = String(existing.start_time || "").slice(0, 8);
      if (previousDate.valid && previousDate.iso === date.iso && previousStart === startTime) return "";
    }
    if (date.iso + "T" + startTime <= businessDateTime(now)) {
      return "Start time must be in the future (Vietnam time).";
    }
    return "";
  }

  root.ScheduleUtils = {
    parseDateInput: parseDateInput,
    parseDateSearch: parseDateSearch,
    matchesDateSearch: matchesDateSearch,
    courtsForVenue: courtsForVenue,
    matchesDateFilter: matchesDateFilter,
    formatDateDisplay: formatDateDisplay,
    selectScheduleDate: selectScheduleDate,
    calendarDays: calendarDays,
    matchesScheduleFilters: matchesScheduleFilters,
    fetchTimeSlotsForCourts: fetchTimeSlotsForCourts,
    refreshDemoSchedule: refreshDemoSchedule,
    emptyFilters: emptyFilters,
    hasTimeSlotOverlap: hasTimeSlotOverlap,
    businessDateTime: businessDateTime,
    validateFutureStart: validateFutureStart
  };
})(typeof window === "undefined" ? globalThis : window);
