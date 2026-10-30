const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const loaderPath = path.join(__dirname, "../assets/js/qr-scanner-loader.js");
const loaderSource = fs.readFileSync(loaderPath, "utf8");

function loadScannerLoader() {
  const events = [];
  let script;
  const window = {};
  const document = {
    currentScript: { src: "http://localhost:8080/assets/js/qr-scanner-loader.js?v=test" },
    createElement: (tag) => { assert.equal(tag, "script"); script = {}; return script; },
    head: { appendChild: (element) => { assert.equal(element, script); } },
    dispatchEvent: (event) => events.push(event.type)
  };
  vm.runInNewContext(loaderSource, { window, document, URL, CustomEvent: class { constructor(type) { this.type = type; } } });
  return { script, window, events };
}

test("QR scanner loader resolves the pinned library from the local vendor directory", () => {
  const { script } = loadScannerLoader();
  assert.equal(script.src, "http://localhost:8080/assets/vendor/html5-qrcode-2.3.8.min.js");
  assert.equal(script.async, true);
  assert.doesNotMatch(script.src, /unpkg\.com/);
});

test("pinned scanner distribution and Apache license are vendored", () => {
  const vendorPath = path.join(__dirname, "../assets/vendor");
  assert.ok(fs.existsSync(path.join(vendorPath, "html5-qrcode-2.3.8.min.js")));
  assert.match(fs.readFileSync(path.join(vendorPath, "html5-qrcode-LICENSE.txt"), "utf8"), /Apache License\s*Version 2\.0/);
  assert.match(fs.readFileSync(path.join(vendorPath, "README.md"), "utf8"), /html5-qrcode.*2\.3\.8/);
});

test("QR scanner loader reports successful library loading", () => {
  const { script, events } = loadScannerLoader();
  script.onload();
  assert.deepEqual(events, ["qrscannerloaded"]);
});

test("QR scanner loader exposes a safe local asset error", () => {
  const { script, window, events } = loadScannerLoader();
  script.onerror();
  assert.match(window.Html5QrcodeLoadError, /local html5-qrcode library/);
  assert.deepEqual(events, ["qrscannerloaderror"]);
});
