const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const appSource = fs.readFileSync(path.join(__dirname, "../assets/js/app.js"), "utf8");
const contract = fs.readFileSync(path.join(__dirname, "../../docs/api/court-service-api-contract.md"), "utf8");

test("Admin Time Slots is a protected route with a dedicated navigation entry", () => {
  assert.match(appSource, /\["admin-schedule", "Time Slots"/);
  assert.match(appSource, /"admin-schedule": \["Platform operations", "Time Slot Management"/);
  assert.match(appSource, /active === "schedule" \|\| active === "admin-schedule"/);
  assert.match(appSource, /requestedAdmin = active\.indexOf\("admin-"\) === 0/);
  assert.match(appSource, /\["admin-dashboard", "admin-venues", "admin-schedule"\]/);
});

test("Admin Time Slots uses live Court Service collections and CRUD endpoints", () => {
  assert.match(appSource, /slots: "\/api\/v1\/time-slots"/);
  assert.match(appSource, /window\.CourtApi\.post\(path, parsed\.values\)/);
  assert.match(appSource, /window\.CourtApi\.put\(path, parsed\.values\)/);
  assert.match(appSource, /window\.CourtApi\.delete\("\/api\/v1\/" \+ resourceForApi\(resource\)/);
  assert.match(appSource, /resourceForApi\(resource\).*"time-slots"/s);
  assert.match(appSource, /function schedulePage\(adminView\)/);
  assert.match(appSource, /authUser\.role === "OWNER" \|\| \(adminView && authUser\.role === "ADMIN"\)/);
  assert.match(contract, /`POST \/api\/v1\/time-slots`/);
  assert.match(contract, /`PUT \/api\/v1\/time-slots\/{slot_id}`/);
  assert.match(contract, /`DELETE \/api\/v1\/time-slots\/{slot_id}`/);
});

test("Admin can write slots while OWNER ownership rules and reservation conflicts stay server-enforced", () => {
  assert.match(appSource, /authUser\.role === "ADMIN" && \["sports", "venues", "courts", "slots"\]/);
  assert.match(appSource, /authUser\.role === "OWNER" && resource !== "sports"/);
  assert.match(appSource, /owner_id=" \+ ownerId/);
  assert.match(contract, /OWNER of related Court's Venue or ADMIN/);
  assert.match(contract, /Slots with an active hold or booking cannot be edited or deactivated/);
  assert.match(appSource, /error\.status === 409/);
  assert.match(appSource, /active HOLD or booking/);
});

test("Admin slot form renders real relationship fields, active state, validation and loading/empty states", () => {
  assert.match(appSource, /formSelect\("Venue", "venue_id"/);
  assert.match(appSource, /data-slot-court required/);
  assert.match(appSource, /calendarPickerMarkup\("slot-date", "Date", record && record\.slot_date/);
  assert.match(appSource, /timeSelect\("Start time", "start_time"/);
  assert.match(appSource, /timeSelect\("End time", "end_time"/);
  assert.match(appSource, /formActiveField\(!record \|\| record\.is_active\)/);
  assert.match(appSource, /Choose start and end times in 30-minute increments/);
  assert.match(appSource, /Loading time slots\.\.\./);
  assert.match(appSource, /No time slots are available yet/);
  assert.match(appSource, /The active flag does not indicate booking availability/);
});
