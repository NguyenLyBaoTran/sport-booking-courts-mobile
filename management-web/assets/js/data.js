window.BookingMockData = {
  ownerBookings: [
    ["BK-2048", "Minh Anh", "Badminton · Court 02", "Oct 23, 2026 · 18:00", "₫180,000", "Confirmed"],
    ["BK-2047", "Quang Huy", "Football · Field A", "Oct 23, 2026 · 17:30", "₫450,000", "Checked in"],
    ["BK-2046", "Thu Hà", "Badminton · Court 01", "Oct 23, 2026 · 17:00", "₫180,000", "Pending"],
    ["BK-2045", "Gia Bảo", "Pickleball · Court 03", "Oct 23, 2026 · 16:30", "₫220,000", "Completed"],
    ["BK-2044", "Phương Linh", "Badminton · Court 02", "Oct 23, 2026 · 16:00", "₫180,000", "Cancelled"]
  ],
  adminBookings: [
    ["BK-2048", "Minh Anh", "Green Field Sports", "Badminton · Court 02", "Oct 23 · 18:00", "₫180,000", "Confirmed"],
    ["BK-2047", "Quang Huy", "City Arena", "Football · Field A", "Oct 23 · 17:30", "₫450,000", "Checked in"],
    ["BK-2046", "Thu Hà", "Green Field Sports", "Badminton · Court 01", "Oct 23 · 17:00", "₫180,000", "Pending"],
    ["BK-2045", "Gia Bảo", "Riverside Courts", "Pickleball · Court 03", "Oct 23 · 16:30", "₫220,000", "Completed"],
    ["BK-2044", "Phương Linh", "City Arena", "Badminton · Court 02", "Oct 23 · 16:00", "₫180,000", "Cancelled"]
  ],
  people: [
    ["U-1042", "Nguyễn Minh Anh", "minhanh@email.com", "User", "Oct 22, 2026", "Active"],
    ["O-0108", "Trần Quốc Bảo", "bao.owner@email.com", "Court Owner", "Oct 20, 2026", "Active"],
    ["U-1041", "Lê Thu Hà", "thuha@email.com", "User", "Oct 19, 2026", "Active"],
    ["O-0107", "Phạm Gia Huy", "huy.owner@email.com", "Court Owner", "Oct 17, 2026", "Pending"],
    ["U-1040", "Võ Phương Linh", "linh@email.com", "User", "Oct 15, 2026", "Inactive"]
  ],
  checkins: [
    ["CI-9031", "BK-2047", "Quang Huy", "City Arena · Field A", "Oct 23, 2026 · 17:22", "Verified"],
    ["CI-9030", "BK-2038", "Nguyễn Hải Nam", "Green Field · Court 01", "Oct 23, 2026 · 16:58", "Verified"],
    ["CI-9029", "BK-2034", "Trần Thanh Tùng", "Riverside · Court 02", "Oct 23, 2026 · 16:40", "Verified"],
    ["CI-9028", "BK-2026", "Lê Hoàng Long", "City Arena · Field B", "Oct 23, 2026 · 15:55", "Manual"]
  ],
  venues: [
    { name: "Green Field Sports Center", area: "Cầu Giấy, Hà Nội", sport: "Badminton", courts: 8, slots: 48, status: "Open", tone: "" },
    { name: "City Arena", area: "Thanh Xuân, Hà Nội", sport: "Football", courts: 4, slots: 26, status: "Open", tone: "court-blue" },
    { name: "Riverside Courts", area: "Tây Hồ, Hà Nội", sport: "Pickleball", courts: 6, slots: 32, status: "Review", tone: "court-clay" },
    { name: "West Lake Badminton", area: "Tây Hồ, Hà Nội", sport: "Badminton", courts: 5, slots: 28, status: "Open", tone: "court-gray" }
  ]
};
