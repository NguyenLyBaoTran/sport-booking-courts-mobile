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
import com.example.sportbooking.utils.BottomNavUtils;
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
        BottomNavUtils.setupBottomNav(this, R.id.navBookings);
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
                if ("PENDING".equals(status)) {
                    if (holder.itemView.getContext() instanceof BookingsActivity) {
                        ((BookingsActivity) holder.itemView.getContext()).confirmAndCancelBooking(booking);
                    }
                } else {
                    Toast.makeText(holder.itemView.getContext(), "Only pending bookings can be cancelled", Toast.LENGTH_SHORT).show();
                }
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
