const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../assets/js/qr-scan-gate.js"), "utf8");
const window = {};
vm.runInNewContext(source, { window });

test("scan gate permits one in-flight request and suppresses the same QR after completion", () => {
  const gate = window.QrScanGate.create();
  let requests = 0;
  const send = (token) => {
    if (!gate.tryBegin(token)) return false;
    requests += 1;
    return true;
  };
  assert.equal(send(" qr-one "), true);
  assert.equal(gate.isPending(), true);
  assert.equal(send("qr-one"), false);
  assert.equal(send("qr-two"), false);
  gate.finish();
  assert.equal(send("qr-one"), false);
  assert.equal(send("qr-two"), true);
  assert.equal(requests, 2);
});

test("stop/start reset allows a controlled retry of a QR after a failed check-in", () => {
  const gate = window.QrScanGate.create();
  assert.equal(gate.tryBegin("qr-invalid"), true);
  gate.finish();
  assert.equal(gate.tryBegin("qr-invalid"), false);
  gate.reset();
  assert.equal(gate.tryBegin("qr-invalid"), true);
});

test("blank QR content is ignored", () => {
  const gate = window.QrScanGate.create();
  assert.equal(gate.tryBegin("  \n "), false);
  assert.equal(gate.isPending(), false);
});
