(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ManagementDateTimeUtils = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function formatVietnamDateTime(value) {
    if (value === null || value === undefined || String(value).trim() === "") return "—";
    var input = String(value).trim();
    var dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input);
    if (dateOnly) {
      var dateCheck = new Date(Date.UTC(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3])));
      if (dateCheck.getUTCFullYear() !== Number(dateOnly[1])
          || dateCheck.getUTCMonth() + 1 !== Number(dateOnly[2])
          || dateCheck.getUTCDate() !== Number(dateOnly[3])) return input;
      return dateOnly[3] + "/" + dateOnly[2] + "/" + dateOnly[1];
    }

    var dateTime = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:?\d{2})?$/i.exec(input);
    if (!dateTime) return input;
    var zone = dateTime[3] || "Z"; // API timestamps without an offset are UTC by contract.
    if (/^[+-]\d{4}$/.test(zone)) zone = zone.slice(0, 3) + ":" + zone.slice(3);
    var parsed = new Date(dateTime[1] + "T" + dateTime[2] + zone);
    if (Number.isNaN(parsed.getTime())) return input;

    var parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23"
    }).formatToParts(parsed).reduce(function (result, part) {
      if (part.type !== "literal") result[part.type] = part.value;
      return result;
    }, {});
    return parts.day + "/" + parts.month + "/" + parts.year + " " + parts.hour + ":" + parts.minute;
  }

  return { formatVietnamDateTime: formatVietnamDateTime };
});
