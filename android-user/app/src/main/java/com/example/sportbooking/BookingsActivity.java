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
import com.example.sportbooking.utils.BottomNavUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.util.List;
import java.text.SimpleDateFormat;
import java.text.ParsePosition;
import java.util.Date;
import java.util.Locale;
import java.util.Calendar;
import java.util.TimeZone;

public class BookingsActivity extends AppCompatActivity {

    private BookingRepository bookingRepository;
    private RecyclerView rvBookings;
    private ProgressBar progressBar;
    private TextView tvEmpty;
    private View tabUpcoming, tabPast;
    private TextView tvUpcoming, tvPast;
    private View indicatorUpcoming, indicatorPast;

    private final List<JsonObject> allBookings = new ArrayList<>();
    private final List<JsonObject> displayedBookings = new ArrayList<>();
    private BookingAdapter bookingAdapter;
    private boolean isUpcomingTab = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_bookings);

        bookingRepository = new BookingRepository(this);

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
        bookingAdapter = new BookingAdapter(displayedBookings, isUpcomingTab, booking -> {
            int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
            if (id > 0) {
                loadBookingDetail(id);
            } else {
                Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
            }
        });
        rvBookings.setAdapter(bookingAdapter);

        tabUpcoming.setOnClickListener(v -> {
            if (!isUpcomingTab) {
                isUpcomingTab = true;
                updateTabUi();
                filterBookings();
            }
        });

        tabPast.setOnClickListener(v -> {
            if (isUpcomingTab) {
                isUpcomingTab = false;
                updateTabUi();
                filterBookings();
            }
        });

        setupBottomNav();
        loadBookings();
    }

    private void updateTabUi() {
        int primaryColor = 0xFF0C8B63; // @color/primary
        int grayColor = 0xFF71829C;  // @color/text_secondary

        if (isUpcomingTab) {
            tvUpcoming.setTextColor(primaryColor);
            indicatorUpcoming.setBackgroundColor(primaryColor);
            tvPast.setTextColor(grayColor);
            indicatorPast.setBackgroundColor(android.graphics.Color.TRANSPARENT);
        } else {
            tvPast.setTextColor(primaryColor);
            indicatorPast.setBackgroundColor(primaryColor);
            tvUpcoming.setTextColor(grayColor);
            indicatorUpcoming.setBackgroundColor(android.graphics.Color.TRANSPARENT);
        }
    }

    private void setupBottomNav() {
        BottomNavUtils.setupBottomNav(this, R.id.navBookings);
    }

    private void filterBookings() {
        displayedBookings.clear();
        for (JsonObject booking : allBookings) {
            String status = booking.has("status") && !booking.get("status").isJsonNull()
                    ? booking.get("status").getAsString().toUpperCase() : "";

            boolean isPast = status.equals("COMPLETED") || status.equals("EXPIRED") || status.equals("CANCELLED") || status.equals("FAILED");

            String slotDate = booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                    ? booking.get("slot_date").getAsString() : "";
            if (isUpcomingTab && status.equals("CONFIRMED") && isUpcomingDate(slotDate)) {
                displayedBookings.add(booking);
            } else if (!isUpcomingTab && isPast) {
                displayedBookings.add(booking);
            }
        }

        bookingAdapter = new BookingAdapter(displayedBookings, isUpcomingTab, booking -> {
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

    private static boolean isUpcomingDate(String slotDate) {
        if (slotDate == null || slotDate.length() < 10) return false;
        String today = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Calendar.getInstance().getTime());
        return slotDate.substring(0, 10).compareTo(today) >= 0;
    }

    private void loadBookingDetail(int bookingId) {
        progressBar.setVisibility(View.VISIBLE);
        bookingRepository.getBooking(bookingId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject booking) {
                progressBar.setVisibility(View.GONE);
                String amount = booking.has("total_amount") && !booking.get("total_amount").isJsonNull()
                        ? booking.get("total_amount").getAsString() : "150,000";
                String slotDate = booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                        ? booking.get("slot_date").getAsString() : "Tue, Apr 22, 2025";
                String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull()
                        ? booking.get("start_time").getAsString() : "11:00 AM";
                String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull()
                        ? booking.get("end_time").getAsString() : "12:00 PM";
                String qrToken = booking.has("qr_token") && !booking.get("qr_token").isJsonNull()
                        ? booking.get("qr_token").getAsString() : null;

                Intent intent = new Intent(BookingsActivity.this, BookingSuccessActivity.class);
                intent.putExtra("booking_id", bookingId);
                intent.putExtra("qr_token", qrToken);
                intent.putExtra("court_name", "Court 1");
                intent.putExtra("venue_name", "Greenfield Sports Complex");
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
                filterBookings();
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
        private final OnBookingClickListener listener;

        public interface OnBookingClickListener {
            void onBookingClick(JsonObject booking);
        }

        public BookingAdapter(List<JsonObject> items, boolean isUpcoming, OnBookingClickListener listener) {
            this.items = items;
            this.isUpcoming = isUpcoming;
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
            String status = booking.has("status") && !booking.get("status").isJsonNull() ? booking.get("status").getAsString() : "CONFIRMED";
            String amount = booking.has("total_amount") && !booking.get("total_amount").isJsonNull() ? booking.get("total_amount").getAsString() : "150,000";
            String slotDate = booking.has("slot_date") && !booking.get("slot_date").isJsonNull() ? booking.get("slot_date").getAsString() : "Tue, Apr 22, 2025";
            String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull() ? booking.get("start_time").getAsString() : "11:00 AM";
            String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull() ? booking.get("end_time").getAsString() : "12:00 PM";
            String confirmedAt = booking.has("confirmed_at") && !booking.get("confirmed_at").isJsonNull()
                    ? booking.get("confirmed_at").getAsString() : null;
            boolean confirmedStatus = "CONFIRMED".equalsIgnoreCase(status);
            boolean canCancel = confirmedStatus && isWithinCancellationWindow(confirmedAt);
            boolean missingConfirmationTime = confirmedStatus && confirmedAt == null;

            holder.tvCourtName.setText("Court 1");
            holder.tvAmount.setText(amount + " VND");
            holder.tvStatus.setText(status);
            holder.tvDate.setText(slotDate);
            holder.tvTime.setText(startTime + " - " + endTime);

            if (isUpcoming) {
                holder.layoutButtonsRow.setVisibility(View.VISIBLE);
                holder.btnViewTicket.setVisibility("CONFIRMED".equalsIgnoreCase(status) ? View.VISIBLE : View.GONE);
                holder.btnCancelBooking.setVisibility(canCancel || missingConfirmationTime ? View.VISIBLE : View.GONE);
                holder.btnCancelBooking.setEnabled(canCancel);
                holder.btnCancelBooking.setText(missingConfirmationTime ? "Cancel unavailable" : "Cancel");
                holder.btnCancelBooking.setOnClickListener(v -> {
                    if (missingConfirmationTime) {
                        Toast.makeText(holder.itemView.getContext(),
                                "Cancellation cannot be offered because this booking has no recorded confirmation time.",
                                Toast.LENGTH_LONG).show();
                    } else if (canCancel) {
                        ((BookingsActivity) holder.itemView.getContext()).confirmAndCancelBooking(booking);
                    }
                });
                holder.btnViewTicket.setOnClickListener(v -> { if ("CONFIRMED".equalsIgnoreCase(status)) listener.onBookingClick(booking); });
                holder.itemView.setOnClickListener(v -> listener.onBookingClick(booking));
            } else {
                // Past tab: hide action buttons and disable click on past tickets
                holder.layoutButtonsRow.setVisibility(View.GONE);
                holder.itemView.setOnClickListener(null);
            }
        }

        private static boolean isWithinCancellationWindow(String value) {
            if (value == null) return false;
            try {
                SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSX", Locale.US);
                format.setTimeZone(TimeZone.getTimeZone("UTC"));
                Date confirmed = format.parse(value, new ParsePosition(0));
                if (confirmed == null) {
                    format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssX", Locale.US);
                    format.setTimeZone(TimeZone.getTimeZone("UTC"));
                    confirmed = format.parse(value, new ParsePosition(0));
                }
                return confirmed != null && System.currentTimeMillis() <= confirmed.getTime() + 30L * 60L * 1000L;
            } catch (Exception ignored) {
                return false;
            }
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
