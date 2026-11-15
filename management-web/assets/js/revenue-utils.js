(function () {
  "use strict";

  var TIME_ZONE = "Asia/Ho_Chi_Minh";

  function dateInTimeZone(value, timeZone) {
    var parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: timeZone || TIME_ZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).formatToParts(value || new Date());
    var values = {};
    parts.forEach(function (part) { values[part.type] = part.value; });
    return values.year + "-" + values.month + "-" + values.day;
  }

  function shiftDate(date, days) {
    var parts = date.split("-").map(Number);
    var value = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2] + days));
    return value.toISOString().slice(0, 10);
  }

  function rangeForPreset(preset, specificDate, now) {
    var today = dateInTimeZone(now || new Date(), TIME_ZONE);
    if (preset === "specific-date") {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(specificDate || "")) return null;
      var parsed = new Date(specificDate + "T00:00:00Z");
      if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== specificDate) return null;
      return { date_from: specificDate, date_to: specificDate, preset: preset, timezone: TIME_ZONE };
    }
    if (preset === "this-month") {
      return {
        date_from: today.slice(0, 8) + "01",
        date_to: shiftDate(today.slice(0, 8) + "01", new Date(Date.UTC(Number(today.slice(0, 4)), Number(today.slice(5, 7)), 0)).getUTCDate() - 1),
        preset: preset,
        timezone: TIME_ZONE
      };
    }
    if (preset === "last-5-days") {
      return { date_from: shiftDate(today, -4), date_to: today, preset: preset, timezone: TIME_ZONE };
    }
    var weekday = new Date(today + "T00:00:00Z").getUTCDay();
    var mondayOffset = (weekday + 6) % 7;
    var monday = shiftDate(today, -mondayOffset);
    return { date_from: monday, date_to: shiftDate(monday, 6), preset: "this-week", timezone: TIME_ZONE };
  }

  function initialFilters(now) {
    var range = rangeForPreset("this-week", "", now);
    return Object.assign(range, { group_by: "day", page: 1, page_size: 20, sort: "desc", specific_date: "" });
  }

  function periodLabel(range) {
    if (!range) return "Select a date";
    var formatter = new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC", day: "2-digit", month: "short", year: "numeric"
    });
    function display(value) { return formatter.format(new Date(value + "T00:00:00Z")); }
    if (range.date_from === range.date_to) return display(range.date_from);
    return display(range.date_from) + " – " + display(range.date_to);
  }

  function chartDate(bucket, groupBy) {
    var value = new Date(bucket + (groupBy === "month" ? "-01" : "") + "T00:00:00Z");
    if (Number.isNaN(value.getTime())) return bucket;
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      day: groupBy === "month" ? undefined : "2-digit",
      month: "short",
      year: groupBy === "month" ? "numeric" : undefined
    }).format(value);
  }

  function csvCell(value) {
    var text = value === null || value === undefined ? "" : String(value);
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }

  function csvDate(value) {
    if (!value) return "";
    var parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) throw new Error("The report contains an invalid payment date.");
    return parsed.toISOString().replace(/\.000Z$/, "Z");
  }

  function buildCsv(items) {
    var headers = ["Payment ID", "Booking ID", "Payment Method", "Amount", "Payment Status", "Payment Date (UTC)"];
    var rows = (items || []).map(function (item) {
      var amount = String(item.amount);
      if (!/^-?\d+(\.\d+)?$/.test(amount)) throw new Error("The report contains an invalid amount.");
      return [item.payment_id, item.booking_id, item.provider, amount, item.status, csvDate(item.payment_date)];
    });
    return "\uFEFF" + [headers].concat(rows).map(function (row) { return row.map(csvCell).join(","); }).join("\r\n");
  }

  window.ManagementRevenueUtils = {
    TIME_ZONE: TIME_ZONE,
    dateInTimeZone: dateInTimeZone,
    rangeForPreset: rangeForPreset,
    initialFilters: initialFilters,
    periodLabel: periodLabel,
    chartDate: chartDate,
    buildCsv: buildCsv
  };
})();
