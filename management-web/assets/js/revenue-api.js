(function () {
  "use strict";

  function getReport(filters) {
    var query = new URLSearchParams();
    Object.keys(filters || {}).forEach(function (key) {
      var value = filters[key];
      if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    });
    var encoded = query.toString();
    return window.CourtApi.get("/api/v1/payments/report" + (encoded ? "?" + encoded : ""));
  }

  function getAllTransactions(filters) {
    var allowedFilters = ["date_from", "date_to", "timezone", "group_by", "sort"];
    var query = { page: 1, page_size: 100 };
    allowedFilters.forEach(function (key) {
      if (filters && filters[key] !== undefined && filters[key] !== null && filters[key] !== "") {
        query[key] = filters[key];
      }
    });
    var items = [];
    var paymentIds = new Set();
    var expectedTotal = null;

    function loadPage(page) {
      query.page = page;
      return getReport(query).then(function (report) {
        var transactionPage = report && report.transactions;
        if (!transactionPage || !Array.isArray(transactionPage.items) ||
            !Number.isInteger(transactionPage.total) || !Number.isInteger(transactionPage.page_size) ||
            transactionPage.page !== page || transactionPage.page_size < 1 || transactionPage.page_size > 100) {
          throw new Error("The report returned an invalid page during export.");
        }
        if (expectedTotal === null) expectedTotal = transactionPage.total;
        if (transactionPage.total !== expectedTotal || transactionPage.items.length > transactionPage.page_size) {
          throw new Error("The report changed while it was being exported. Please try again.");
        }
        transactionPage.items.forEach(function (item) {
          var id = String(item && item.payment_id);
          if (!item || item.payment_id === undefined || paymentIds.has(id)) {
            throw new Error("The report changed while it was being exported. Please try again.");
          }
          paymentIds.add(id);
          items.push(item);
        });
        if (items.length > expectedTotal) throw new Error("The report changed while it was being exported. Please try again.");
        if (items.length < expectedTotal) {
          if (transactionPage.items.length === 0) throw new Error("The report ended before all transactions were exported.");
          return loadPage(page + 1);
        }
        if (items.length !== expectedTotal) throw new Error("The report changed while it was being exported. Please try again.");
        return items;
      });
    }

    return loadPage(1);
  }

  window.ManagementRevenueApi = { getReport: getReport, getAllTransactions: getAllTransactions };
})();
