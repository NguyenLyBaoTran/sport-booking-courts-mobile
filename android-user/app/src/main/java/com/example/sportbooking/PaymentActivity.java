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
import java.util.Locale;

public class PaymentActivity extends AppCompatActivity {

    private int bookingId;
    private String totalAmount, courtName, dateStr;

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
        totalAmount = getIntent().getStringExtra("total_amount");
        courtName = getIntent().getStringExtra("court_name");
        dateStr = getIntent().getStringExtra("date");

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
        if (totalAmount != null && !totalAmount.isEmpty()) {
            String formatted = formatPrice(totalAmount);
            tvSummaryPrice.setText(formatted + " / hour");
            tvTotalAmount.setText(formatted);
        }

        ivBack.setOnClickListener(v -> finish());
        btnPayNow.setOnClickListener(v -> processPayment());
    }

    private String formatPrice(String rawAmount) {
        if (rawAmount == null || rawAmount.trim().isEmpty()) {
            return "150,000 VND";
        }
        try {
            double val = Double.parseDouble(rawAmount);
            if (val < 1000) {
                val = val * 1000;
            }
            NumberFormat nf = NumberFormat.getInstance(Locale.getDefault());
            return nf.format(val) + " VND";
        } catch (Exception e) {
            return rawAmount + " VND";
        }
    }

    private void processPayment() {
        if (bookingId == -1) {
            Toast.makeText(this, "Invalid booking ID", Toast.LENGTH_SHORT).show();
            return;
        }

        btnPayNow.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);

        paymentRepository.processPayment(bookingId, "SUCCESS", new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                progressBar.setVisibility(View.GONE);
                String paymentStatus = result.has("status") && !result.get("status").isJsonNull()
                        ? result.get("status").getAsString() : "";
                if (!"PAID".equalsIgnoreCase(paymentStatus)) {
                    btnPayNow.setEnabled(true);
                    Toast.makeText(PaymentActivity.this,
                            "Payment failed. Please try again.", Toast.LENGTH_LONG).show();
                    return;
                }
                String qrToken = result.has("qr_token") && !result.get("qr_token").isJsonNull()
                        ? result.get("qr_token").getAsString() : null;

                Intent intent = new Intent(PaymentActivity.this, BookingSuccessActivity.class);
                intent.putExtra("booking_id", bookingId);
                intent.putExtra("qr_token", qrToken);
                intent.putExtra("total_amount", totalAmount);
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
