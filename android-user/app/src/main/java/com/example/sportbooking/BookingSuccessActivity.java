package com.example.sportbooking;

import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.utils.QrCodeUtils;

public class BookingSuccessActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_booking_success);

        int bookingId = getIntent().getIntExtra("booking_id", -1);
        String qrToken = getIntent().getStringExtra("qr_token");
        String totalAmount = getIntent().getStringExtra("total_amount");

        TextView tvDetails = findViewById(R.id.tvSuccessDetails);
        ImageView ivQr = findViewById(R.id.ivQrCode);
        Button btnViewBookings = findViewById(R.id.btnViewBookings);
        Button btnHome = findViewById(R.id.btnHome);

        tvDetails.setText("Booking #" + bookingId + " Confirmed!\nAmount Paid: " + (totalAmount == null || totalAmount.trim().isEmpty() ? "N/A" : "$" + totalAmount));

        if (qrToken != null && !qrToken.trim().isEmpty()) {
            try {
                Bitmap qrBitmap = QrCodeUtils.generateQRCode(qrToken, 400, 400);
                ivQr.setImageBitmap(qrBitmap);
            } catch (Exception e) {
                ivQr.setVisibility(android.view.View.GONE);
                Toast.makeText(this, "Failed to generate QR code", Toast.LENGTH_SHORT).show();
            }
        } else {
            ivQr.setVisibility(android.view.View.GONE);
        }

        btnViewBookings.setOnClickListener(v -> {
            startActivity(new Intent(this, BookingsActivity.class));
            finish();
        });

        btnHome.setOnClickListener(v -> {
            Intent intent = new Intent(this, MainActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(intent);
            finish();
        });
    }
}
