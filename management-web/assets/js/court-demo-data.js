(function () {
  "use strict";

  function localDateString(date) {
    return [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0")
    ].join("-");
  }

  function createDemoData() {
    var sports = [
      { id: 1, name: "Badminton", description: "Indoor court sport", is_active: true },
      { id: 2, name: "Football", description: "Small-sided football", is_active: true },
      { id: 3, name: "Pickleball", description: "Paddle court sport", is_active: true }
    ];
    var venues = [
      { id: 1, owner_id: null, name: "Demo Sports Center A", address: "Fictitious address, District 1, Ho Chi Minh City", description: "Demo-only venue.", phone: "0900000001", is_active: true, created_at: null },
      { id: 2, owner_id: null, name: "Demo Sports Center B", address: "Fictitious address, District 3, Ho Chi Minh City", description: "Demo-only venue.", phone: "0900000002", is_active: true, created_at: null }
    ];
    var courts = [
      { id: 1, venue_id: 1, sport_id: 1, name: "Badminton Court 1", description: "Demo court", price_per_hour: "120000.00", is_active: true },
      { id: 2, venue_id: 1, sport_id: 2, name: "Football Court 1", description: "Demo court", price_per_hour: "500000.00", is_active: true },
      { id: 3, venue_id: 1, sport_id: 3, name: "Pickleball Court 1", description: "Demo court", price_per_hour: "150000.00", is_active: true },
      { id: 4, venue_id: 2, sport_id: 1, name: "Badminton Court 2", description: "Demo court", price_per_hour: "120000.00", is_active: true },
      { id: 5, venue_id: 2, sport_id: 2, name: "Football Court 2", description: "Demo court", price_per_hour: "500000.00", is_active: true },
      { id: 6, venue_id: 2, sport_id: 3, name: "Pickleball Court 2", description: "Demo court", price_per_hour: "150000.00", is_active: true }
    ];
    var today = localDateString(new Date());
    var slots = [];
    courts.forEach(function (court) {
      slots.push({ id: slots.length + 1, court_id: court.id, slot_date: today, start_time: "08:00:00", end_time: "09:00:00", is_active: true });
      slots.push({ id: slots.length + 1, court_id: court.id, slot_date: today, start_time: "18:00:00", end_time: "19:00:00", is_active: true });
    });
    return { sports: sports, venues: venues, courts: courts, slots: slots };
  }

  window.CourtDemoData = { create: createDemoData };
})();
