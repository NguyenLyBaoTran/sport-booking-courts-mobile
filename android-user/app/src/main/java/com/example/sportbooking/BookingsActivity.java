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
import com.example.sportbooking.repository.PaymentRepository;
import com.example.sportbooking.utils.BottomNavUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.text.NumberFormat;
import java.util.Locale;
import java.util.List;

public class BookingsActivity extends AppCompatActivity {

    private BookingRepository bookingRepository;
    private PaymentRepository paymentRepository;
    private RecyclerView rvBookings;
    private ProgressBar progressBar;
    private TextView tvEmpty;
    private View tabUpcoming, tabPast, tabPayments;
    private TextView tvUpcoming, tvPast, tvPayments;
    private View indicatorUpcoming, indicatorPast, indicatorPayments;

    private final List<JsonObject> allBookings = new ArrayList<>();
    private final List<JsonObject> displayedBookings = new ArrayList<>();
    private final List<JsonObject> displayedPayments = new ArrayList<>();
    private BookingAdapter bookingAdapter;
    private int selectedTab = 0;
    private boolean resumedOnce;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_bookings);

        bookingRepository = new BookingRepository(this);
        paymentRepository = new PaymentRepository(this);

        rvBookings = findViewById(R.id.rvBookings);
        progressBar = findViewById(R.id.progressBar);
        tvEmpty = findViewById(R.id.tvEmpty);
        tabUpcoming = findViewById(R.id.tabUpcoming);
        tabPast = findViewById(R.id.tabPast);
        tabPayments = findViewById(R.id.tabPayments);
        tvUpcoming = findViewById(R.id.tvUpcoming);
        tvPast = findViewById(R.id.tvPast);
        tvPayments = findViewById(R.id.tvPayments);
        indicatorUpcoming = findViewById(R.id.indicatorUpcoming);
        indicatorPast = findViewById(R.id.indicatorPast);
        indicatorPayments = findViewById(R.id.indicatorPayments);

        rvBookings.setLayoutManager(new LinearLayoutManager(this));
        bookingAdapter = new BookingAdapter(displayedBookings, true, false, booking -> {
            int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
            if (id > 0) {
                loadBookingDetail(id);
            } else {
                Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
            }
        });
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
        tabPayments.setOnClickListener(v -> {
            if (selectedTab != 2) {
                selectedTab = 2;
                updateTabUi();
                loadPayments();
            }
        });

        setupBottomNav();
        loadBookings();
    }

    private void updateTabUi() {
        int primaryColor = 0xFF0C8B63; // @color/primary
        int grayColor = 0xFF71829C;  // @color/text_secondary

        tvUpcoming.setTextColor(selectedTab == 0 ? primaryColor : grayColor);
        indicatorUpcoming.setBackgroundColor(selectedTab == 0 ? primaryColor : android.graphics.Color.TRANSPARENT);
        tvPast.setTextColor(selectedTab == 1 ? primaryColor : grayColor);
        indicatorPast.setBackgroundColor(selectedTab == 1 ? primaryColor : android.graphics.Color.TRANSPARENT);
        tvPayments.setTextColor(selectedTab == 2 ? primaryColor : grayColor);
        indicatorPayments.setBackgroundColor(selectedTab == 2 ? primaryColor : android.graphics.Color.TRANSPARENT);
    }

    private void setupBottomNav() {
        BottomNavUtils.setupBottomNav(this, R.id.navBookings);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (resumedOnce) {
            if (selectedTab == 2) loadPayments();
            else loadBookings();
        } else {
            resumedOnce = true;
        }
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

        bookingAdapter = new BookingAdapter(displayedBookings, selectedTab == 0, false, booking -> {
            int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
            if (id > 0) {
                loadBookingDetail(id);
            } else {
                Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
            }
        });
        rvBookings.setAdapter(bookingAdapter);
        tvEmpty.setVisibility(displayedBookings.isEmpty() ? View.VISIBLE : View.GONE);
    }

    private void loadPayments() {
        progressBar.setVisibility(View.VISIBLE);
        tvEmpty.setVisibility(View.GONE);
        displayedPayments.clear();
        paymentRepository.getPayments(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray result) {
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) displayedPayments.add(result.get(i).getAsJsonObject());
                bookingAdapter = new BookingAdapter(displayedPayments, false, true, null);
                rvBookings.setAdapter(bookingAdapter);
                tvEmpty.setText("No payment transactions found.");
                tvEmpty.setVisibility(displayedPayments.isEmpty() ? View.VISIBLE : View.GONE);
            }
            @Override public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                tvEmpty.setText(error);
                tvEmpty.setVisibility(View.VISIBLE);
            }
        });
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

    private void loadBookings() {
        progressBar.setVisibility(View.VISIBLE);
        tvEmpty.setVisibility(View.GONE);
        allBookings.clear();
        displayedBookings.clear();
        bookingAdapter.notifyDataSetChanged();

        bookingRepository.getBookings(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) {
                    allBookings.add(result.get(i).getAsJsonObject());
                }
                if (selectedTab != 2) filterBookings();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                tvEmpty.setVisibility(View.VISIBLE);
                Toast.makeText(BookingsActivity.this, error, Toast.LENGTH_SHORT).show();
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
                loadBookings();
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
        private final boolean isPayment;
        private final OnBookingClickListener listener;

        public interface OnBookingClickListener {
            void onBookingClick(JsonObject booking);
        }

        public BookingAdapter(List<JsonObject> items, boolean isUpcoming, boolean isPayment, OnBookingClickListener listener) {
            this.items = items;
            this.isUpcoming = isUpcoming;
            this.isPayment = isPayment;
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
            if (isPayment) {
                int bookingId = booking.has("booking_id") ? booking.get("booking_id").getAsInt() : -1;
                holder.tvCourtName.setText("Payment #" + id + (bookingId > 0 ? " · Booking #" + bookingId : ""));
                holder.tvDate.setText(booking.has("created_at") ? booking.get("created_at").getAsString() : "");
                holder.tvTime.setText(booking.has("transaction_code") && !booking.get("transaction_code").isJsonNull()
                        ? "Transaction " + booking.get("transaction_code").getAsString() : "");
            } else {
                int courtId = booking.has("court_id") && !booking.get("court_id").isJsonNull() ? booking.get("court_id").getAsInt() : -1;
                holder.tvCourtName.setText(courtId > 0 ? "Court #" + courtId : "Booking #" + id);
                holder.tvDate.setText(booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                        ? booking.get("slot_date").getAsString() : "");
                String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull() ? formatTime(booking.get("start_time").getAsString()) : "";
                String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull() ? formatTime(booking.get("end_time").getAsString()) : "";
                holder.tvTime.setText(startTime + (endTime.isEmpty() ? "" : " - " + endTime));
            }
            holder.tvAmount.setText(amount.isEmpty() ? "" : formatAmount(amount) + " VND");
            holder.tvStatus.setText(status);
            if (isPayment) {
                holder.layoutButtonsRow.setVisibility(View.GONE);
                holder.itemView.setOnClickListener(null);
            } else if ("PENDING".equalsIgnoreCase(status)
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
                // Past tab: hide action buttons and disable click on past tickets
                holder.layoutButtonsRow.setVisibility(View.GONE);
                holder.itemView.setOnClickListener(null);
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
            TextView tvCourtName, tvAmount, tvStatus, tvDate, tvTime;
            Button btnCancelBooking, btnViewTicket;
            View layoutButtonsRow;

            ViewHolder(View itemView) {
                super(itemView);
                tvCourtName = itemView.findViewById(R.id.tvBookingCourtName);
                tvAmount = itemView.findViewById(R.id.tvBookingAmount);
                tvStatus = itemView.findViewById(R.id.tvBookingStatus);
                tvDate = itemView.findViewById(R.id.tvBookingDate);
                tvTime = itemView.findViewById(R.id.tvBookingTime);
                btnCancelBooking = itemView.findViewById(R.id.btnCancelBooking);
                btnViewTicket = itemView.findViewById(R.id.btnViewTicket);
                layoutButtonsRow = itemView.findViewById(R.id.layoutButtonsRow);
            }
        }
    }
}
