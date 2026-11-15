package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.BookingRepository;
import com.example.sportbooking.repository.CourtRepository;
import com.example.sportbooking.repository.PaymentRepository;
import com.example.sportbooking.utils.BottomNavUtils;
import com.example.sportbooking.utils.CustomerUiUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.text.NumberFormat;
import java.util.Locale;
import java.util.List;
import java.util.HashMap;
import java.util.Map;

public class BookingsActivity extends AppCompatActivity {

    public static final String EXTRA_REFRESH_BOOKINGS = "refresh_bookings";

    private BookingRepository bookingRepository;
    private PaymentRepository paymentRepository;
    private CourtRepository courtRepository;
    private RecyclerView rvBookings;
    private ProgressBar progressBar;
    private TextView tvEmpty;
    private View tabUpcoming, tabPast;
    private TextView tvUpcoming, tvPast;
    private View indicatorUpcoming, indicatorPast;

    private final List<JsonObject> allBookings = new ArrayList<>();
    private final List<JsonObject> displayedBookings = new ArrayList<>();
    private final Map<Integer, JsonObject> paymentsByBooking = new HashMap<>();
    private final Map<Integer, String> courtNames = new HashMap<>();
    private final Map<Integer, String> venueNames = new HashMap<>();
    private BookingAdapter bookingAdapter;
    private int selectedTab = 0;
    private int historyRequestId;
    private boolean paymentsAvailable = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_bookings);

        bookingRepository = new BookingRepository(this);
        paymentRepository = new PaymentRepository(this);
        courtRepository = new CourtRepository(this);

        rvBookings = findViewById(R.id.rvBookings);
        progressBar = findViewById(R.id.progressBar);
        tvEmpty = findViewById(R.id.tvEmpty);
        tabUpcoming = findViewById(R.id.tabUpcoming);
        tabPast = findViewById(R.id.tabPast);
        tvUpcoming = findViewById(R.id.tvUpcoming);
        tvPast = findViewById(R.id.tvPast);
        indicatorUpcoming = findViewById(R.id.indicatorUpcoming);
        indicatorPast = findViewById(R.id.indicatorPast);

        rvBookings.setLayoutManager(new LinearLayoutManager(this));
        bookingAdapter = createBookingAdapter(true);
        rvBookings.setAdapter(bookingAdapter);

        tabUpcoming.setOnClickListener(v -> {
            if (selectedTab != 0) {
                selectedTab = 0;
                updateTabUi();
                filterBookings();
            }
        });

        tabPast.setOnClickListener(v -> {
            if (selectedTab != 1) {
                selectedTab = 1;
                updateTabUi();
                filterBookings();
            }
        });
        setupBottomNav();
        loadHistory();
        loadCatalogueNames();
    }

    private void updateTabUi() {
        int primaryColor = 0xFF0C8B63; // @color/primary
        int grayColor = 0xFF71829C;  // @color/text_secondary

        tvUpcoming.setTextColor(selectedTab == 0 ? primaryColor : grayColor);
        indicatorUpcoming.setBackgroundColor(selectedTab == 0 ? primaryColor : android.graphics.Color.TRANSPARENT);
        tvPast.setTextColor(selectedTab == 1 ? primaryColor : grayColor);
        indicatorPast.setBackgroundColor(selectedTab == 1 ? primaryColor : android.graphics.Color.TRANSPARENT);
    }

    private void setupBottomNav() {
        BottomNavUtils.setupBottomNav(this, R.id.navBookings);
    }

    @Override
    protected void onResume() {
        super.onResume();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent.getBooleanExtra(EXTRA_REFRESH_BOOKINGS, false)) loadHistory();
    }

    @Override
    public void onBackPressed() {
        BottomNavUtils.handleBack(this);
    }

    private void filterBookings() {
        displayedBookings.clear();
        for (JsonObject booking : allBookings) {
            String status = booking.has("status") && !booking.get("status").isJsonNull()
                    ? booking.get("status").getAsString().toUpperCase() : "";

            boolean upcoming = booking.has("is_upcoming") && booking.get("is_upcoming").getAsBoolean();
            if (selectedTab == 0 && status.equals("CONFIRMED") && upcoming) {
                displayedBookings.add(booking);
            } else if (selectedTab == 1 && !(status.equals("CONFIRMED") && upcoming)) {
                displayedBookings.add(booking);
            }
        }

        bookingAdapter = createBookingAdapter(selectedTab == 0);
        rvBookings.setAdapter(bookingAdapter);
        tvEmpty.setVisibility(displayedBookings.isEmpty() ? View.VISIBLE : View.GONE);
    }

    private BookingAdapter createBookingAdapter(boolean upcoming) {
        return new BookingAdapter(displayedBookings, upcoming, paymentsByBooking, paymentsAvailable,
                courtNames, venueNames, booking -> {
                    int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
                    if (id <= 0) {
                        Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
                    } else if (CustomerUiUtils.isCompletedBooking(stringValue(booking, "status"))) {
                        openReceipt(booking);
                    } else {
                        loadBookingDetail(id);
                    }
                });
    }

    private void loadHistory() {
        final int requestId = ++historyRequestId;
        progressBar.setVisibility(View.VISIBLE);
        tvEmpty.setVisibility(View.GONE);
        tvEmpty.setText("No bookings found.");
        allBookings.clear();
        displayedBookings.clear();
        paymentsByBooking.clear();
        bookingAdapter.notifyDataSetChanged();
        final int[] pending = {2};
        final boolean[] bookingsFailed = {false};
        Runnable finishPart = () -> {
            pending[0] -= 1;
            if (pending[0] != 0 || requestId != historyRequestId) return;
            progressBar.setVisibility(View.GONE);
            if (bookingsFailed[0]) {
                tvEmpty.setText("Could not load bookings. Check your connection and try again.");
                tvEmpty.setVisibility(View.VISIBLE);
                return;
            }
            filterBookings();
        };

        bookingRepository.getBookings(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray result) {
                if (requestId != historyRequestId) return;
                for (int i = 0; i < result.size(); i++) allBookings.add(result.get(i).getAsJsonObject());
                finishPart.run();
            }
            @Override public void onError(String error) {
                if (requestId != historyRequestId) return;
                bookingsFailed[0] = true;
                finishPart.run();
            }
        });

        paymentRepository.getPayments(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray result) {
                if (requestId != historyRequestId) return;
                paymentsAvailable = true;
                for (int i = 0; i < result.size(); i++) {
                    JsonObject payment = result.get(i).getAsJsonObject();
                    if (!payment.has("booking_id") || payment.get("booking_id").isJsonNull()) continue;
                    int bookingId = payment.get("booking_id").getAsInt();
                    if (!paymentsByBooking.containsKey(bookingId)) paymentsByBooking.put(bookingId, payment);
                }
                finishPart.run();
            }
            @Override public void onError(String error) {
                if (requestId != historyRequestId) return;
                paymentsAvailable = false;
                finishPart.run();
            }
        });
    }

    private void loadCatalogueNames() {
        courtRepository.getVenues(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray result) {
                venueNames.clear();
                for (int i = 0; i < result.size(); i++) {
                    JsonObject venue = result.get(i).getAsJsonObject();
                    if (venue.has("id") && venue.has("name")) venueNames.put(venue.get("id").getAsInt(), venue.get("name").getAsString());
                }
                bookingAdapter.notifyDataSetChanged();
            }
            @Override public void onError(String error) { }
        });
        courtRepository.searchCourts(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray result) {
                courtNames.clear();
                for (int i = 0; i < result.size(); i++) {
                    JsonObject court = result.get(i).getAsJsonObject();
                    if (court.has("id") && court.has("name")) courtNames.put(court.get("id").getAsInt(), court.get("name").getAsString());
                }
                bookingAdapter.notifyDataSetChanged();
            }
            @Override public void onError(String error) { }
        });
    }

    private static String stringValue(JsonObject object, String key) {
        return object.has(key) && !object.get(key).isJsonNull() ? object.get(key).getAsString() : "";
    }

    private void openReceipt(JsonObject booking) {
        int bookingId = booking.get("id").getAsInt();
        Intent intent = new Intent(this, BookingReceiptActivity.class);
        intent.putExtra("booking_id", bookingId);
        JsonObject payment = paymentsByBooking.get(bookingId);
        if (payment != null) intent.putExtra("payment_json", payment.toString());
        startActivity(intent);
    }

    private void loadBookingDetail(int bookingId) {
        progressBar.setVisibility(View.VISIBLE);
        bookingRepository.getBooking(bookingId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject booking) {
                progressBar.setVisibility(View.GONE);
                String amount = booking.has("total_amount") && !booking.get("total_amount").isJsonNull()
                        ? booking.get("total_amount").getAsString() : "";
                String slotDate = booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                        ? booking.get("slot_date").getAsString() : "";
                String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull()
                        ? BookingAdapter.formatTime(booking.get("start_time").getAsString()) : "";
                String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull()
                        ? BookingAdapter.formatTime(booking.get("end_time").getAsString()) : "";
                String qrToken = booking.has("qr_token") && !booking.get("qr_token").isJsonNull()
                        ? booking.get("qr_token").getAsString() : null;

                Intent intent = new Intent(BookingsActivity.this, BookingSuccessActivity.class);
                intent.putExtra("booking_id", bookingId);
                intent.putExtra("qr_token", qrToken);
                intent.putExtra("court_name", booking.has("court_id") && !booking.get("court_id").isJsonNull()
                        ? "Court #" + booking.get("court_id").getAsString() : "");
                intent.putExtra("venue_name", booking.has("venue_id") && !booking.get("venue_id").isJsonNull()
                        ? "Venue #" + booking.get("venue_id").getAsString() : "");
                intent.putExtra("date", slotDate);
                intent.putExtra("time_slot", startTime + " - " + endTime);
                intent.putExtra("total_amount", amount);
                startActivity(intent);
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                Toast.makeText(BookingsActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void confirmAndCancelBooking(JsonObject booking) {
        int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
        if (id <= 0) {
            Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
            return;
        }

        new AlertDialog.Builder(this)
                .setTitle("Cancel booking")
                .setMessage("Cancel booking #" + id + "? The held time slot will be released.")
                .setNegativeButton("Keep booking", null)
                .setPositiveButton("Cancel booking", (dialog, which) -> cancelBooking(id))
                .show();
    }

    private void cancelBooking(int bookingId) {
        progressBar.setVisibility(View.VISIBLE);
        bookingRepository.cancelBooking(bookingId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                Toast.makeText(BookingsActivity.this, "Booking cancelled", Toast.LENGTH_SHORT).show();
                loadHistory();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                Toast.makeText(BookingsActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
    }

    public static class BookingAdapter extends RecyclerView.Adapter<BookingAdapter.ViewHolder> {
        private final List<JsonObject> items;
        private final boolean isUpcoming;
        private final Map<Integer, JsonObject> paymentsByBooking;
        private final boolean paymentsAvailable;
        private final Map<Integer, String> courtNames;
        private final Map<Integer, String> venueNames;
        private final OnBookingClickListener listener;

        public interface OnBookingClickListener {
            void onBookingClick(JsonObject booking);
        }

        public BookingAdapter(List<JsonObject> items, boolean isUpcoming,
                              Map<Integer, JsonObject> paymentsByBooking, boolean paymentsAvailable,
                              Map<Integer, String> courtNames, Map<Integer, String> venueNames,
                              OnBookingClickListener listener) {
            this.items = items;
            this.isUpcoming = isUpcoming;
            this.paymentsByBooking = paymentsByBooking;
            this.paymentsAvailable = paymentsAvailable;
            this.courtNames = courtNames;
            this.venueNames = venueNames;
            this.listener = listener;
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_booking, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            JsonObject booking = items.get(position);
            int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
            String status = booking.has("status") && !booking.get("status").isJsonNull() ? booking.get("status").getAsString() : "UNKNOWN";
            String amount = booking.has("amount") && !booking.get("amount").isJsonNull()
                    ? booking.get("amount").getAsString()
                    : booking.has("total_amount") && !booking.get("total_amount").isJsonNull() ? booking.get("total_amount").getAsString() : "";
            int courtId = booking.has("court_id") && !booking.get("court_id").isJsonNull() ? booking.get("court_id").getAsInt() : -1;
            int venueId = booking.has("venue_id") && !booking.get("venue_id").isJsonNull() ? booking.get("venue_id").getAsInt() : -1;
            String court = courtNames.get(courtId);
            holder.tvCourtName.setText(court != null ? court : (courtId > 0 ? "Court #" + courtId : "Booking #" + id));
            String venue = venueNames.get(venueId);
            holder.tvVenue.setText(venue != null ? venue : (venueId > 0 ? "Venue #" + venueId : ""));
            holder.tvVenue.setVisibility(venueId > 0 ? View.VISIBLE : View.GONE);
            holder.tvDate.setText(booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                    ? booking.get("slot_date").getAsString() : "");
            String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull() ? formatTime(booking.get("start_time").getAsString()) : "";
            String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull() ? formatTime(booking.get("end_time").getAsString()) : "";
            holder.tvTime.setText(startTime + (endTime.isEmpty() ? "" : " - " + endTime));
            holder.tvAmount.setText(amount.isEmpty() ? "" : formatAmount(amount) + " VND");
            holder.tvStatus.setText(status);
            JsonObject payment = paymentsByBooking.get(id);
            if (!paymentsAvailable) {
                holder.tvPayment.setText("Payment information unavailable");
                holder.tvPayment.setVisibility(View.VISIBLE);
            } else if (payment != null) {
                String paymentStatus = payment.has("status") && !payment.get("status").isJsonNull()
                        ? payment.get("status").getAsString() : "Unknown";
                String method = CustomerUiUtils.paymentMethodLabel(
                        payment.has("provider") && !payment.get("provider").isJsonNull()
                                ? payment.get("provider").getAsString() : null);
                holder.tvPayment.setText("Payment: " + paymentStatus + " · " + method);
                holder.tvPayment.setVisibility(View.VISIBLE);
            } else {
                holder.tvPayment.setText("Payment: No record");
                holder.tvPayment.setVisibility(View.VISIBLE);
            }
            if ("PENDING".equalsIgnoreCase(status)
                    && booking.has("can_cancel") && booking.get("can_cancel").getAsBoolean()) {
                holder.layoutButtonsRow.setVisibility(View.VISIBLE);
                holder.btnViewTicket.setVisibility(View.GONE);
                holder.btnCancelBooking.setVisibility(View.VISIBLE);
                holder.btnCancelBooking.setEnabled(true);
                holder.btnCancelBooking.setOnClickListener(v -> ((BookingsActivity) holder.itemView.getContext()).confirmAndCancelBooking(booking));
                holder.itemView.setOnClickListener(null);
            } else if (isUpcoming) {
                holder.layoutButtonsRow.setVisibility(View.VISIBLE);
                boolean confirmedStatus = "CONFIRMED".equalsIgnoreCase(status);
                boolean canCancel = booking.has("can_cancel") && booking.get("can_cancel").getAsBoolean();
                holder.btnViewTicket.setVisibility(confirmedStatus ? View.VISIBLE : View.GONE);
                holder.btnCancelBooking.setVisibility(canCancel ? View.VISIBLE : View.GONE);
                holder.btnCancelBooking.setEnabled(canCancel);
                holder.btnCancelBooking.setOnClickListener(v -> ((BookingsActivity) holder.itemView.getContext()).confirmAndCancelBooking(booking));
                holder.btnViewTicket.setOnClickListener(v -> { if (confirmedStatus && listener != null) listener.onBookingClick(booking); });
                holder.itemView.setOnClickListener(v -> { if (confirmedStatus && listener != null) listener.onBookingClick(booking); });
            } else {
                holder.layoutButtonsRow.setVisibility(View.GONE);
                boolean completed = CustomerUiUtils.isCompletedBooking(status);
                holder.itemView.setOnClickListener(completed && listener != null ? v -> listener.onBookingClick(booking) : null);
            }
        }

        private static String formatTime(String value) {
            return value != null && value.length() >= 5 ? value.substring(0, 5) : value;
        }

        private static String formatAmount(String value) {
            try { return NumberFormat.getNumberInstance(Locale.getDefault()).format(Double.parseDouble(value)); }
            catch (Exception ignored) { return value; }
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        static class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvCourtName, tvVenue, tvAmount, tvStatus, tvDate, tvTime, tvPayment;
            Button btnCancelBooking, btnViewTicket;
            View layoutButtonsRow;

            ViewHolder(View itemView) {
                super(itemView);
                tvCourtName = itemView.findViewById(R.id.tvBookingCourtName);
                tvVenue = itemView.findViewById(R.id.tvBookingVenue);
                tvAmount = itemView.findViewById(R.id.tvBookingAmount);
                tvStatus = itemView.findViewById(R.id.tvBookingStatus);
                tvDate = itemView.findViewById(R.id.tvBookingDate);
                tvTime = itemView.findViewById(R.id.tvBookingTime);
                tvPayment = itemView.findViewById(R.id.tvBookingPayment);
                btnCancelBooking = itemView.findViewById(R.id.btnCancelBooking);
                btnViewTicket = itemView.findViewById(R.id.btnViewTicket);
                layoutButtonsRow = itemView.findViewById(R.id.layoutButtonsRow);
            }
        }
    }
}
