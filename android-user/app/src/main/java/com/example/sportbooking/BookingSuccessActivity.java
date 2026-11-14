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

import com.example.sportbooking.repository.BookingRepository;
import com.example.sportbooking.utils.QrCodeUtils;
import com.google.gson.JsonObject;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class BookingSuccessActivity extends AppCompatActivity {

    private BookingRepository bookingRepository;

    private LinearLayout layoutQrView, layoutSuccessView, layoutBottomBar;
    private TextView tvCourtName, tvVenueName, tvTicketDate, tvTicketTime;
    private TextView tvSuccessCourtName, tvSuccessVenueName, tvSuccessCustomer;
    private TextView tvSuccessBookingId, tvSuccessBookingDate, tvSuccessTimeSlot, tvSuccessMessage;
    private TextView tvSuccessIcon;
    private ImageView ivQrCode;
    private Button btnDone;

    private int bookingId = -1;
    private String qrToken, courtName, venueName, dateStr, timeSlotStr, customerName;
    private final Handler pollHandler = new Handler(Looper.getMainLooper());
    private Runnable pollRunnable;
    private Call<JsonObject> statusCall;
    private boolean screenResumed;
    private boolean requestInFlight;
    private boolean terminalStatus;
    private boolean inactiveMessageShown;
    private int requestGeneration;

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
        tvSuccessBookingId = findViewById(R.id.tvSuccessBookingId);
        tvSuccessBookingDate = findViewById(R.id.tvSuccessBookingDate);
        tvSuccessTimeSlot = findViewById(R.id.tvSuccessTimeSlot);
        tvSuccessMessage = findViewById(R.id.tvSuccessMessage);
        tvSuccessIcon = findViewById(R.id.tvSuccessIcon);
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
        // Do not render the QR until Booking Service confirms the current state.
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

    private void showCheckinSuccessView() {
        layoutQrView.setVisibility(View.GONE);
        layoutSuccessView.setVisibility(View.VISIBLE);
        layoutBottomBar.setVisibility(View.VISIBLE);
        tvSuccessIcon.setText("\u2713");
        tvSuccessMessage.setText("CHECK-IN SUCCESSFUL");
    }

    private void checkBookingStatus() {
        if (!shouldPoll(screenResumed, terminalStatus, requestInFlight) || bookingId <= 0) return;

        requestInFlight = true;
        final int generation = ++requestGeneration;
        statusCall = bookingRepository.getBookingRequest(bookingId);
        statusCall.enqueue(new Callback<JsonObject>() {
            @Override
            public void onResponse(Call<JsonObject> call, Response<JsonObject> response) {
                if (generation != requestGeneration) return;
                requestInFlight = false;
                statusCall = null;
                if (!screenResumed || isFinishing() || isDestroyed()) return;

                if (!response.isSuccessful() || response.body() == null) {
                    int code = response.code();
                    if (code == 401 || code == 403 || code == 404) {
                        showInactiveTicket("This booking is no longer available.");
                    } else {
                        scheduleNextPoll();
                    }
                    return;
                }

                applyBookingStatus(response.body());
            }

            @Override
            public void onFailure(Call<JsonObject> call, Throwable throwable) {
                if (generation != requestGeneration) return;
                requestInFlight = false;
                statusCall = null;
                if (screenResumed && !isFinishing() && !isDestroyed()) scheduleNextPoll();
            }
        });
    }

    private void applyBookingStatus(JsonObject booking) {
        String status = booking.has("status") && !booking.get("status").isJsonNull()
                ? booking.get("status").getAsString() : "";
        bindBookingDetails(booking);

        if (isCheckInConfirmed(status)) {
            terminalStatus = true;
            stopPolling();
            showCheckinSuccessView();
            return;
        }

        if (isActiveQrStatus(status)) {
            String previousQrToken = qrToken;
            qrToken = booking.has("qr_token") && !booking.get("qr_token").isJsonNull()
                    ? booking.get("qr_token").getAsString() : null;
            if (qrToken == null || qrToken.trim().isEmpty()) {
                showInactiveTicket("This confirmed booking has no active QR ticket.");
                return;
            }
            if (layoutQrView.getVisibility() != View.VISIBLE || !qrToken.equals(previousQrToken)) {
                showQrView();
            }
            scheduleNextPoll();
            return;
        }

        showInactiveTicket("This booking does not have an active ticket.");
    }

    private void bindBookingDetails(JsonObject booking) {
        String currentCourt = booking.has("court_id") && !booking.get("court_id").isJsonNull()
                ? "Court #" + booking.get("court_id").getAsString() : courtName;
        String currentVenue = booking.has("venue_id") && !booking.get("venue_id").isJsonNull()
                ? "Venue #" + booking.get("venue_id").getAsString() : venueName;
        String currentDate = booking.has("slot_date") && !booking.get("slot_date").isJsonNull()
                ? booking.get("slot_date").getAsString() : dateStr;
        String startTime = booking.has("start_time") && !booking.get("start_time").isJsonNull()
                ? formatTime(booking.get("start_time").getAsString()) : "";
        String endTime = booking.has("end_time") && !booking.get("end_time").isJsonNull()
                ? formatTime(booking.get("end_time").getAsString()) : "";
        String currentTime = !startTime.isEmpty() && !endTime.isEmpty()
                ? startTime + " - " + endTime : timeSlotStr;

        courtName = currentCourt;
        venueName = currentVenue;
        dateStr = currentDate;
        timeSlotStr = currentTime;
        if (currentCourt != null) {
            tvCourtName.setText(currentCourt);
            tvSuccessCourtName.setText(currentCourt);
        }
        if (currentVenue != null) {
            tvVenueName.setText(currentVenue);
            tvSuccessVenueName.setText(currentVenue);
        }
        if (currentDate != null) {
            tvTicketDate.setText(currentDate);
            tvSuccessBookingDate.setText(currentDate);
        }
        if (currentTime != null) {
            tvTicketTime.setText(currentTime);
            tvSuccessTimeSlot.setText(currentTime);
        }
        tvSuccessBookingId.setText("Booking #" + bookingId);
        if (booking.has("user_id") && !booking.get("user_id").isJsonNull()) {
            tvSuccessCustomer.setText("Customer #" + booking.get("user_id").getAsString());
        }
    }

    static String formatTime(String value) {
        return value != null && value.length() >= 5 ? value.substring(0, 5) : value;
    }

    static boolean isCheckInConfirmed(String status) {
        return "CHECKED_IN".equalsIgnoreCase(status);
    }

    static boolean isActiveQrStatus(String status) {
        return "CONFIRMED".equalsIgnoreCase(status);
    }

    static boolean shouldPoll(boolean resumed, boolean terminal, boolean inFlight) {
        return resumed && !terminal && !inFlight;
    }

    private void showInactiveTicket(String message) {
        terminalStatus = true;
        stopPolling();
        layoutQrView.setVisibility(View.GONE);
        layoutSuccessView.setVisibility(View.GONE);
        layoutBottomBar.setVisibility(View.VISIBLE);
        ivQrCode.setImageDrawable(null);
        if (!inactiveMessageShown) {
            inactiveMessageShown = true;
            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
        }
    }

    private void scheduleNextPoll() {
        if (!shouldPoll(screenResumed, terminalStatus, requestInFlight) || pollRunnable != null) return;
        pollRunnable = () -> {
            pollRunnable = null;
            checkBookingStatus();
        };
        pollHandler.postDelayed(pollRunnable, 2500);
    }

    private void stopPolling() {
        if (pollRunnable != null) {
            pollHandler.removeCallbacks(pollRunnable);
            pollRunnable = null;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        screenResumed = true;
        checkBookingStatus();
    }

    @Override
    protected void onPause() {
        screenResumed = false;
        stopPolling();
        requestGeneration++;
        requestInFlight = false;
        if (statusCall != null) {
            statusCall.cancel();
            statusCall = null;
        }
        super.onPause();
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
        screenResumed = false;
        stopPolling();
        requestGeneration++;
        if (statusCall != null) {
            statusCall.cancel();
            statusCall = null;
        }
        super.onDestroy();
    }
}
