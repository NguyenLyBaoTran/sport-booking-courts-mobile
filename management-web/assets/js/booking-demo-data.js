(function () {
  "use strict";

  function createDemoBookings() {
    return [
      { id: "BK-3106", customer: { name: "Nguyen Minh Anh", email: "minhanh@example.test", phone: "0900000106" }, venue: "Demo Sports Center A", court: "Badminton Court 1", date: "2026-10-24", start_time: "18:00", end_time: "19:00", total_amount: 180000, status: "CONFIRMED", payment_status: "SUCCESS", checkin_status: null, created_at: "2026-10-24T09:15:00" },
      { id: "BK-3105", customer: { name: "Tran Quang Huy", email: "quanghuy@example.test", phone: "0900000105" }, venue: "Demo Sports Center A", court: "Football Court 1", date: "2026-10-24", start_time: "17:30", end_time: "18:30", total_amount: 450000, status: "CHECKED_IN", payment_status: "SUCCESS", checkin_status: "CHECKED_IN", created_at: "2026-10-24T08:50:00" },
      { id: "BK-3104", customer: { name: "Le Thu Ha", email: "thuha@example.test", phone: "0900000104" }, venue: "Demo Sports Center B", court: "Badminton Court 2", date: "2026-10-25", start_time: "09:00", end_time: "10:00", total_amount: 180000, status: "PENDING", payment_status: "PENDING", checkin_status: null, created_at: "2026-10-24T08:20:00" },
      { id: "BK-3103", customer: { name: "Pham Gia Bao", email: "giabao@example.test", phone: "0900000103" }, venue: "Demo Sports Center B", court: "Pickleball Court 2", date: "2026-10-23", start_time: "16:30", end_time: "17:30", total_amount: 220000, status: "COMPLETED", payment_status: "SUCCESS", checkin_status: "CHECKED_IN", created_at: "2026-10-23T10:05:00" },
      { id: "BK-3102", customer: { name: "Vo Phuong Linh", email: "linh@example.test", phone: "0900000102" }, venue: "Demo Sports Center A", court: "Badminton Court 1", date: "2026-10-23", start_time: "15:00", end_time: "16:00", total_amount: 180000, status: "CANCELLED", payment_status: "REFUNDED", checkin_status: null, created_at: "2026-10-22T13:40:00" },
      { id: "BK-3101", customer: { name: "Do Hai Nam", email: "hainam@example.test", phone: "0900000101" }, venue: "Demo Sports Center B", court: "Football Court 2", date: "2026-10-26", start_time: "20:00", end_time: "21:00", total_amount: 450000, status: "EXPIRED", payment_status: "UNPAID", checkin_status: null, created_at: "2026-10-22T09:00:00" }
    ];
  }

  window.BookingDemoData = { create: createDemoBookings };
})();
