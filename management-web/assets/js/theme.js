(function (root) {
  "use strict";

  var storageKey = "courtbook-theme";
  var current = "light";

  try {
    current = root.localStorage.getItem(storageKey) === "dark" ? "dark" : "light";
  } catch (error) {
    current = "light";
  }

  function apply(theme, persist) {
    current = theme === "dark" ? "dark" : "light";
    root.document.documentElement.setAttribute("data-theme", current);
    if (persist) {
      try { root.localStorage.setItem(storageKey, current); } catch (error) { /* Theme still applies for this page view. */ }
    }
    return current;
  }

  apply(current, false);
  root.ManagementTheme = {
    get: function () { return current; },
    set: function (theme) { return apply(theme, true); }
  };
})(window);
