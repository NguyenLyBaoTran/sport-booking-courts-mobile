const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../assets/js/theme.js"), "utf8");

function loadTheme(storage) {
  const attributes = {};
  const window = {
    localStorage: storage,
    document: { documentElement: { setAttribute: (name, value) => { attributes[name] = value; } } }
  };
  vm.runInNewContext(source, { window });
  return { theme: window.ManagementTheme, attributes };
}

test("theme defaults to Light and applies the saved choice before rendering", () => {
  const values = new Map();
  const { theme, attributes } = loadTheme({ getItem: (key) => values.get(key) || null, setItem: (key, value) => values.set(key, value) });
  assert.equal(theme.get(), "light");
  assert.equal(attributes["data-theme"], "light");
  theme.set("dark");
  assert.equal(theme.get(), "dark");
  assert.equal(attributes["data-theme"], "dark");
  assert.equal(values.get("courtbook-theme"), "dark");
  const reloaded = loadTheme({ getItem: (key) => values.get(key) || null, setItem: (key, value) => values.set(key, value) });
  assert.equal(reloaded.theme.get(), "dark");
  assert.equal(reloaded.attributes["data-theme"], "dark");
  reloaded.theme.set("light");
  assert.equal(values.get("courtbook-theme"), "light");
});

test("invalid saved theme and unavailable localStorage safely use Light", () => {
  const invalid = loadTheme({ getItem: () => "sepia", setItem: () => {} });
  assert.equal(invalid.theme.get(), "light");
  assert.equal(invalid.attributes["data-theme"], "light");
  const blocked = loadTheme({ getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } });
  assert.equal(blocked.theme.get(), "light");
  assert.equal(blocked.theme.set("dark"), "dark");
  assert.equal(blocked.attributes["data-theme"], "dark");
});
