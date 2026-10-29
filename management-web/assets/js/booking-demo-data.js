(function () {
  "use strict";

  function createDemoBookings() {
    return [
      { id: "BK-3106", customer: { name: "Nguyen Minh Anh", email: "minhanh@example.test", phone: "0900000106" }, venue: "Demo Sports Center A", court: "Badminton Court 1", date: "2026-10-24", start_time: "18:00", end_time: "19:00", total_amount: 180000, status: "CONFIRMED", owner_id: "demo-owner", qr_token: "demo-qr-confirmed-3106", payment_status: "SUCCESS", checkin_status: null, created_at: "2026-10-24T09:15:00" },
      { id: "BK-3105", customer: { name: "Tran Quang Huy", email: "quanghuy@example.test", phone: "0900000105" }, venue: "Demo Sports Center A", court: "Football Court 1", date: "2026-10-24", start_time: "17:30", end_time: "18:30", total_amount: 450000, status: "CHECKED_IN", owner_id: "demo-owner", qr_token: "demo-qr-checked-in-3105", payment_status: "SUCCESS", checkin_status: "CHECKED_IN", created_at: "2026-10-24T08:50:00" },
      { id: "BK-3104", customer: { name: "Le Thu Ha", email: "thuha@example.test", phone: "0900000104" }, venue: "Demo Sports Center B", court: "Badminton Court 2", date: "2026-10-25", start_time: "09:00", end_time: "10:00", total_amount: 180000, status: "PENDING", owner_id: "demo-owner", qr_token: "demo-qr-pending-3104", payment_status: "PENDING", checkin_status: null, created_at: "2026-10-24T08:20:00" },
      { id: "BK-3103", customer: { name: "Pham Gia Bao", email: "giabao@example.test", phone: "0900000103" }, venue: "Demo Sports Center B", court: "Pickleball Court 2", date: "2026-10-23", start_time: "16:30", end_time: "17:30", total_amount: 220000, status: "COMPLETED", owner_id: "demo-owner", qr_token: "demo-qr-completed-3103", payment_status: "SUCCESS", checkin_status: "CHECKED_IN", created_at: "2026-10-23T10:05:00" },
      { id: "BK-3102", customer: { name: "Vo Phuong Linh", email: "linh@example.test", phone: "0900000102" }, venue: "Demo Sports Center A", court: "Badminton Court 1", date: "2026-10-23", start_time: "15:00", end_time: "16:00", total_amount: 180000, status: "CANCELLED", owner_id: "demo-owner", qr_token: "demo-qr-cancelled-3102", payment_status: "REFUNDED", checkin_status: null, created_at: "2026-10-22T13:40:00" },
      { id: "BK-3101", customer: { name: "Do Hai Nam", email: "hainam@example.test", phone: "0900000101" }, venue: "Demo Sports Center B", court: "Football Court 2", date: "2026-10-26", start_time: "20:00", end_time: "21:00", total_amount: 450000, status: "EXPIRED", owner_id: "demo-owner", qr_token: "demo-qr-expired-3101", payment_status: "UNPAID", checkin_status: null, created_at: "2026-10-22T09:00:00" },
      { id: "BK-3199", customer: { name: "Other Owner Customer", email: "other-owner@example.test", phone: "0900000199" }, venue: "Other Owner Venue", court: "Other Owner Court", date: "2026-10-24", start_time: "12:00", end_time: "13:00", total_amount: 200000, status: "CONFIRMED", owner_id: "other-demo-owner", qr_token: "demo-qr-other-owner-3199", payment_status: "SUCCESS", checkin_status: null, created_at: "2026-10-24T07:00:00" }
    ];
  }

  window.BookingDemoData = { create: createDemoBookings };
})();
