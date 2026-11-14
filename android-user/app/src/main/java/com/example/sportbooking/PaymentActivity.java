package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.PaymentRepository;
import com.google.gson.JsonObject;

import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class PaymentActivity extends AppCompatActivity {

    private int bookingId = -1;
    private int[] timeSlotIds;
    private String totalAmount, courtName, dateStr, timeRange;

    private PaymentRepository paymentRepository;

    private TextView tvSummaryCourtName, tvSummaryDate, tvSummaryPrice, tvTotalAmount;
    private Button btnPayNow;
    private ProgressBar progressBar;
    private ImageView ivBack;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_payment);

        bookingId = getIntent().getIntExtra("booking_id", -1);
        timeSlotIds = getIntent().getIntArrayExtra("time_slot_ids");
        if (timeSlotIds == null) {
            int legacySlotId = getIntent().getIntExtra("time_slot_id", -1);
            if (legacySlotId > 0) timeSlotIds = new int[]{legacySlotId};
        }
        totalAmount = getIntent().getStringExtra("total_amount");
        courtName = getIntent().getStringExtra("court_name");
        dateStr = getIntent().getStringExtra("date");
        timeRange = getIntent().getStringExtra("time_slot");

        paymentRepository = new PaymentRepository(this);

        ivBack = findViewById(R.id.ivBack);
        tvSummaryCourtName = findViewById(R.id.tvSummaryCourtName);
        tvSummaryDate = findViewById(R.id.tvSummaryDate);
        tvSummaryPrice = findViewById(R.id.tvSummaryPrice);
        tvTotalAmount = findViewById(R.id.tvTotalAmount);
        btnPayNow = findViewById(R.id.btnPayNow);
        progressBar = findViewById(R.id.progressBar);

        if (courtName != null && !courtName.isEmpty()) {
            tvSummaryCourtName.setText(courtName);
        }
        if (dateStr != null && !dateStr.isEmpty()) {
            tvSummaryDate.setText(dateStr);
        }
        if (timeRange != null && !timeRange.isEmpty()) {
            ((TextView) findViewById(R.id.tvSummaryTimeSlot)).setText(timeRange);
        }
        if (totalAmount != null && !totalAmount.isEmpty()) {
            String formatted = formatPrice(totalAmount);
            tvSummaryPrice.setText(getIntent().getIntExtra("duration_minutes", 0) > 0
                    ? (getIntent().getIntExtra("duration_minutes", 0) / 60.0) + " hours" : "Booking total");
            tvTotalAmount.setText(formatted);
        } else {
            btnPayNow.setEnabled(false);
            Toast.makeText(this, "A valid booking quote is required before payment.", Toast.LENGTH_LONG).show();
        }

        ivBack.setOnClickListener(v -> finish());
        btnPayNow.setOnClickListener(v -> processPayment());
    }

    private String formatPrice(String rawAmount) {
        if (rawAmount == null || rawAmount.trim().isEmpty()) {
            return "Price unavailable";
        }
        try {
            double val = Double.parseDouble(rawAmount);
            NumberFormat nf = NumberFormat.getInstance(Locale.getDefault());
            return nf.format(val) + " VND";
        } catch (Exception e) {
            return "Price unavailable";
        }
    }

    private void processPayment() {
        if (bookingId == -1 && (timeSlotIds == null || timeSlotIds.length == 0)) {
            Toast.makeText(this, "Invalid time slot", Toast.LENGTH_SHORT).show();
            return;
        }

        btnPayNow.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);

        if (bookingId > 0) {
            submitPayment();
            return;
        }
        List<Integer> selectedIds = new ArrayList<>();
        for (int slotId : timeSlotIds) selectedIds.add(slotId);
        new com.example.sportbooking.repository.BookingRepository(this).createBooking(selectedIds, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject booking) {
                bookingId = booking.has("id") ? booking.get("id").getAsInt() : -1;
                if (bookingId <= 0 || !booking.has("status") || !"PENDING".equals(booking.get("status").getAsString())) {
                    progressBar.setVisibility(View.GONE);
                    btnPayNow.setEnabled(true);
                    Toast.makeText(PaymentActivity.this, "Slot could not be reserved. Please choose another.", Toast.LENGTH_LONG).show();
                    return;
                }
                if (booking.has("total_amount") && !booking.get("total_amount").isJsonNull()) {
                    totalAmount = booking.get("total_amount").getAsString();
                    tvTotalAmount.setText(formatPrice(totalAmount));
                }
                submitPayment();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                btnPayNow.setEnabled(true);
                Toast.makeText(PaymentActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void submitPayment() {
        paymentRepository.processPayment(bookingId, "SUCCESS", new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                progressBar.setVisibility(View.GONE);
                String paymentStatus = result.has("status") && !result.get("status").isJsonNull()
                        ? result.get("status").getAsString() : "";
                if (!"PAID".equalsIgnoreCase(paymentStatus)) {
                    if ("FAILED".equalsIgnoreCase(paymentStatus)) bookingId = -1;
                    btnPayNow.setEnabled(true);
                    Toast.makeText(PaymentActivity.this, "Payment failed. Please review the slot availability and try again.", Toast.LENGTH_LONG).show();
                    return;
                }
                String qrToken = result.has("qr_token") && !result.get("qr_token").isJsonNull()
                        ? result.get("qr_token").getAsString() : null;

                Intent intent = new Intent(PaymentActivity.this, BookingSuccessActivity.class);
                intent.putExtra("booking_id", bookingId);
                intent.putExtra("qr_token", qrToken);
                intent.putExtra("total_amount", totalAmount);
                intent.putExtra("date", dateStr);
                intent.putExtra("time_slot", timeRange);
                startActivity(intent);
                finish();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                btnPayNow.setEnabled(true);
                Toast.makeText(PaymentActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
    }
}
