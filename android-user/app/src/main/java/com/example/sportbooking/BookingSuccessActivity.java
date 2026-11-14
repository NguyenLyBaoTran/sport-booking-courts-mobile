package com.example.sportbooking;

import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.BookingRepository;
import com.example.sportbooking.utils.QrCodeUtils;
import com.google.gson.JsonObject;

public class BookingSuccessActivity extends AppCompatActivity {

    private BookingRepository bookingRepository;

    private LinearLayout layoutQrView, layoutSuccessView, layoutBottomBar;
    private TextView tvCourtName, tvVenueName, tvTicketDate, tvTicketTime;
    private TextView tvSuccessCourtName, tvSuccessVenueName, tvSuccessCustomer, tvSuccessTimeSlot;
    private ImageView ivQrCode;
    private Button btnDone;

    private int bookingId = -1;
    private String qrToken, courtName, venueName, dateStr, timeSlotStr, customerName;
    private final Handler pollHandler = new Handler(Looper.getMainLooper());
    private Runnable pollRunnable;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_booking_success);

        bookingRepository = new BookingRepository(this);

        bookingId = getIntent().getIntExtra("booking_id", -1);
        qrToken = getIntent().getStringExtra("qr_token");
        courtName = getIntent().getStringExtra("court_name");
        venueName = getIntent().getStringExtra("venue_name");
        dateStr = getIntent().getStringExtra("date");
        timeSlotStr = getIntent().getStringExtra("time_slot");
        customerName = getIntent().getStringExtra("customer_name");

        layoutQrView = findViewById(R.id.layoutQrView);
        layoutSuccessView = findViewById(R.id.layoutSuccessView);
        layoutBottomBar = findViewById(R.id.layoutBottomBar);

        tvCourtName = findViewById(R.id.tvCourtName);
        tvVenueName = findViewById(R.id.tvVenueName);
        tvTicketDate = findViewById(R.id.tvTicketDate);
        tvTicketTime = findViewById(R.id.tvTicketTime);
        ivQrCode = findViewById(R.id.ivQrCode);

        tvSuccessCourtName = findViewById(R.id.tvSuccessCourtName);
        tvSuccessVenueName = findViewById(R.id.tvSuccessVenueName);
        tvSuccessCustomer = findViewById(R.id.tvSuccessCustomer);
        tvSuccessTimeSlot = findViewById(R.id.tvSuccessTimeSlot);
        btnDone = findViewById(R.id.btnDone);

        // Bind initial Intent data
        if (courtName != null && !courtName.isEmpty()) {
            tvCourtName.setText(courtName);
            tvSuccessCourtName.setText(courtName);
        }
        if (venueName != null && !venueName.isEmpty()) {
            tvVenueName.setText(venueName);
            tvSuccessVenueName.setText(venueName);
        }
        if (dateStr != null && !dateStr.isEmpty()) {
            tvTicketDate.setText(dateStr);
        }
        if (timeSlotStr != null && !timeSlotStr.isEmpty()) {
            tvTicketTime.setText(timeSlotStr);
            tvSuccessTimeSlot.setText(timeSlotStr);
        }
        if (customerName != null && !customerName.isEmpty()) {
            tvSuccessCustomer.setText(customerName);
        }

        btnDone.setOnClickListener(v -> finishToBookings());

        layoutQrView.setVisibility(View.GONE);
        layoutBottomBar.setVisibility(View.GONE);
        // Fetch and validate the authoritative booking before rendering its QR.
        checkBookingStatus();
    }

    private void showQrView() {
        layoutQrView.setVisibility(View.VISIBLE);
        layoutSuccessView.setVisibility(View.GONE);
        layoutBottomBar.setVisibility(View.GONE);

        if (qrToken == null || qrToken.trim().isEmpty()) {
            layoutQrView.setVisibility(View.GONE);
            layoutSuccessView.setVisibility(View.GONE);
            layoutBottomBar.setVisibility(View.VISIBLE);
            return;
        }
        String token = qrToken;
        try {
            Bitmap qrBitmap = QrCodeUtils.generateQRCode(token, 400, 400);
            ivQrCode.setImageBitmap(qrBitmap);
        } catch (Exception ignored) {
        }
    }

    private void showCheckinSuccessView(String status) {
        layoutQrView.setVisibility(View.GONE);
        layoutSuccessView.setVisibility(View.VISIBLE);
        layoutBottomBar.setVisibility(View.VISIBLE);
    }

    private void checkBookingStatus() {
        if (bookingId <= 0) return;

        bookingRepository.getBooking(bookingId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject booking) {
                String status = booking.has("status") && !booking.get("status").isJsonNull()
                        ? booking.get("status").getAsString() : "CONFIRMED";

                qrToken = booking.has("qr_token") && !booking.get("qr_token").isJsonNull()
                        ? booking.get("qr_token").getAsString() : null;
                if ("CONFIRMED".equalsIgnoreCase(status)) {
                    stopPolling();
                    showQrView();
                    return;
                }

                if ("CHECKED_IN".equalsIgnoreCase(status) || "COMPLETED".equalsIgnoreCase(status)) {
                    stopPolling();
                    showCheckinSuccessView(status);
                } else {
                    stopPolling();
                    layoutQrView.setVisibility(View.GONE);
                    layoutSuccessView.setVisibility(View.GONE);
                    layoutBottomBar.setVisibility(View.VISIBLE);
                    Toast.makeText(BookingSuccessActivity.this, "This booking does not have an active ticket.", Toast.LENGTH_LONG).show();
                }
            }

            @Override
            public void onError(String error) {
                stopPolling();
                layoutQrView.setVisibility(View.GONE);
                layoutBottomBar.setVisibility(View.VISIBLE);
                Toast.makeText(BookingSuccessActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void startPolling() {
        stopPolling();
        pollRunnable = this::checkBookingStatus;
        pollHandler.postDelayed(pollRunnable, 3000);
    }

    private void stopPolling() {
        if (pollRunnable != null) {
            pollHandler.removeCallbacks(pollRunnable);
            pollRunnable = null;
        }
    }

    private void finishToBookings() {
        stopPolling();
        Intent intent = new Intent(this, BookingsActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(intent);
        finish();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopPolling();
    }
}
