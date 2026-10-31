package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
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
import com.example.sportbooking.utils.QrCodeUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.util.List;

public class BookingsActivity extends AppCompatActivity {

    private BookingRepository bookingRepository;
    private RecyclerView rvBookings;
    private ProgressBar progressBar;
    private TextView tvEmpty;

    private final List<JsonObject> bookingList = new ArrayList<>();
    private BookingAdapter bookingAdapter;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_bookings);

        bookingRepository = new BookingRepository(this);

        rvBookings = findViewById(R.id.rvBookings);
        progressBar = findViewById(R.id.progressBar);
        tvEmpty = findViewById(R.id.tvEmpty);

        rvBookings.setLayoutManager(new LinearLayoutManager(this));
        bookingAdapter = new BookingAdapter(bookingList, booking -> {
            int id = booking.has("id") ? booking.get("id").getAsInt() : -1;
            if (id > 0) {
                loadBookingDetail(id);
            } else {
                Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
            }
        });
        rvBookings.setAdapter(bookingAdapter);

        setupBottomNav();
        loadBookings();
    }

    private void setupBottomNav() {
        View bottomNav = findViewById(R.id.bottomNav);
        if (bottomNav != null) {
            bottomNav.findViewById(R.id.navHome).setOnClickListener(v -> {
                startActivity(new Intent(this, MainActivity.class));
                finish();
            });
            bottomNav.findViewById(R.id.navSearch).setOnClickListener(v -> {
                startActivity(new Intent(this, CourtSearchActivity.class));
                finish();
            });
            bottomNav.findViewById(R.id.navBookings).setOnClickListener(v -> {
                // already here
            });
            bottomNav.findViewById(R.id.navProfile).setOnClickListener(v -> {
                Toast.makeText(this, "Profile feature", Toast.LENGTH_SHORT).show();
            });
        }
    }

    private void loadBookingDetail(int bookingId) {
        progressBar.setVisibility(View.VISIBLE);
        bookingRepository.getBooking(bookingId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject booking) {
                progressBar.setVisibility(View.GONE);
                String status = booking.has("status") && !booking.get("status").isJsonNull()
                        ? booking.get("status").getAsString() : "UNKNOWN";
                String amount = booking.has("total_amount") && !booking.get("total_amount").isJsonNull()
                        ? booking.get("total_amount").getAsString() : "N/A";
                String slotDate = booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                        ? booking.get("slot_date").getAsString() : "N/A";
                String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull()
                        ? booking.get("start_time").getAsString() : "";
                String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull()
                        ? booking.get("end_time").getAsString() : "";
                String schedule = slotDate + (startTime.isEmpty() ? "" : "  " + startTime + " - " + endTime);
                String message = "Booking #" + bookingId + "\nStatus: " + status + "\nAmount: " + amount + " VND\nSchedule: " + schedule;

                AlertDialog.Builder builder = new AlertDialog.Builder(BookingsActivity.this)
                        .setTitle("Booking Ticket & Details")
                        .setMessage(message)
                        .setPositiveButton("Close", null);

                String qrToken = booking.has("qr_token") && !booking.get("qr_token").isJsonNull()
                        ? booking.get("qr_token").getAsString() : null;
                if (qrToken != null && !qrToken.trim().isEmpty()) {
                    try {
                        ImageView qrImage = new ImageView(BookingsActivity.this);
                        int size = 220 * getResources().getDisplayMetrics().densityDpi / 160;
                        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(size, size);
                        params.gravity = android.view.Gravity.CENTER;
                        qrImage.setLayoutParams(params);
                        qrImage.setAdjustViewBounds(true);
                        qrImage.setImageBitmap(QrCodeUtils.generateQRCode(qrToken, 220, 220));
                        builder.setView(qrImage);
                    } catch (Exception ignored) {
                    }
                }
                builder.show();
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
        bookingList.clear();
        bookingAdapter.notifyDataSetChanged();

        bookingRepository.getBookings(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) {
                    bookingList.add(result.get(i).getAsJsonObject());
                }
                bookingAdapter.notifyDataSetChanged();
                tvEmpty.setVisibility(bookingList.isEmpty() ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                tvEmpty.setVisibility(View.VISIBLE);
                Toast.makeText(BookingsActivity.this, error, Toast.LENGTH_SHORT).show();
            }
        });
    }

    public static class BookingAdapter extends RecyclerView.Adapter<BookingAdapter.ViewHolder> {
        private final List<JsonObject> items;
        private final OnBookingClickListener listener;

        public interface OnBookingClickListener {
            void onBookingClick(JsonObject booking);
        }

        public BookingAdapter(List<JsonObject> items, OnBookingClickListener listener) {
            this.items = items;
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

            holder.tvCourtName.setText("Court 1");
            holder.tvAmount.setText(amount + " VND");
            holder.tvStatus.setText(status);
            holder.tvDate.setText(slotDate);
            holder.tvTime.setText(startTime + " - " + endTime);

            holder.btnViewTicket.setOnClickListener(v -> listener.onBookingClick(booking));
            holder.btnCancelBooking.setOnClickListener(v -> {
                Toast.makeText(holder.itemView.getContext(), "Booking #" + id + " cancelled", Toast.LENGTH_SHORT).show();
            });
            holder.itemView.setOnClickListener(v -> listener.onBookingClick(booking));
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        static class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvCourtName, tvAmount, tvStatus, tvDate, tvTime;
            Button btnCancelBooking, btnViewTicket;

            ViewHolder(View itemView) {
                super(itemView);
                tvCourtName = itemView.findViewById(R.id.tvBookingCourtName);
                tvAmount = itemView.findViewById(R.id.tvBookingAmount);
                tvStatus = itemView.findViewById(R.id.tvBookingStatus);
                tvDate = itemView.findViewById(R.id.tvBookingDate);
                tvTime = itemView.findViewById(R.id.tvBookingTime);
                btnCancelBooking = itemView.findViewById(R.id.btnCancelBooking);
                btnViewTicket = itemView.findViewById(R.id.btnViewTicket);
            }
        }
    }
}
