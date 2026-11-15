package com.example.sportbooking;

import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.BookingRepository;
import com.example.sportbooking.repository.CourtRepository;
import com.example.sportbooking.repository.PaymentRepository;
import com.example.sportbooking.utils.CustomerUiUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class BookingReceiptActivity extends AppCompatActivity {
    private BookingRepository bookingRepository;
    private CourtRepository courtRepository;
    private PaymentRepository paymentRepository;
    private int bookingId;
    private JsonObject payment;
    private TextView tvReference, tvStatus, tvCourt, tvVenue, tvSport, tvDate, tvTime,
            tvDuration, tvCreated, tvPaymentMethod, tvPaymentReference, tvPaymentStatus,
            tvPaymentTime, tvTotal, tvReceiptError;
    private View receiptContent;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_booking_receipt);
        bookingRepository = new BookingRepository(this);
        courtRepository = new CourtRepository(this);
        paymentRepository = new PaymentRepository(this);
        bindViews();
        bookingId = getIntent().getIntExtra("booking_id", -1);
        String paymentJson = getIntent().getStringExtra("payment_json");
        if (paymentJson != null) {
            try { payment = JsonParser.parseString(paymentJson).getAsJsonObject(); }
            catch (Exception ignored) { payment = null; }
        }
        Button back = findViewById(R.id.btnReceiptBack);
        back.setOnClickListener(v -> finish());
        if (bookingId <= 0) {
            showError("Booking reference is unavailable.");
            return;
        }
        loadBooking();
        if (payment == null || !matchesPayment(payment)) loadPayment();
        else bindPayment(payment);
    }

    private void bindViews() {
        receiptContent = findViewById(R.id.receiptContent);
        tvReceiptError = findViewById(R.id.tvReceiptError);
        tvReference = findViewById(R.id.tvReceiptReference);
        tvStatus = findViewById(R.id.tvReceiptStatus);
        tvCourt = findViewById(R.id.tvReceiptCourt);
        tvVenue = findViewById(R.id.tvReceiptVenue);
        tvSport = findViewById(R.id.tvReceiptSport);
        tvDate = findViewById(R.id.tvReceiptDate);
        tvTime = findViewById(R.id.tvReceiptTime);
        tvDuration = findViewById(R.id.tvReceiptDuration);
        tvCreated = findViewById(R.id.tvReceiptCreated);
        tvPaymentMethod = findViewById(R.id.tvReceiptPaymentMethod);
        tvPaymentReference = findViewById(R.id.tvReceiptPaymentReference);
        tvPaymentStatus = findViewById(R.id.tvReceiptPaymentStatus);
        tvPaymentTime = findViewById(R.id.tvReceiptPaymentTime);
        tvTotal = findViewById(R.id.tvReceiptTotal);
    }

    private void loadBooking() {
        bookingRepository.getBooking(bookingId, new ApiCallback<JsonObject>() {
            @Override public void onSuccess(JsonObject booking) {
                String status = value(booking, "status");
                if (!"COMPLETED".equalsIgnoreCase(status)) {
                    showError("This booking is no longer completed, so a completed receipt is unavailable.");
                    return;
                }
                receiptContent.setVisibility(View.VISIBLE);
                tvReceiptError.setVisibility(View.GONE);
                tvReference.setText("Booking #" + bookingId);
                tvStatus.setText(status);
                tvDate.setText(CustomerUiUtils.formatBookingDate(valueOr(booking, "slot_date", "Unavailable")));
                String start = formatTime(value(booking, "start_time"));
                String end = formatTime(value(booking, "end_time"));
                tvTime.setText(start.isEmpty() || end.isEmpty() ? "Unavailable" : start + " - " + end);
                tvDuration.setText(CustomerUiUtils.durationLabel(value(booking, "start_time"), value(booking, "end_time")));
                String createdAt = value(booking, "created_at");
                tvCreated.setText(createdAt.isEmpty() ? "Created: Not recorded"
                        : "Created: " + CustomerUiUtils.formatUtcTimestamp(createdAt));
                String amount = value(booking, "total_amount");
                tvTotal.setText(amount.isEmpty() ? "Unavailable" : CustomerUiUtils.formatAmount(amount) + " VND");
                tvCourt.setText(booking.has("court_id") && !booking.get("court_id").isJsonNull()
                        ? "Court #" + value(booking, "court_id") : "Unavailable");
                tvVenue.setText(booking.has("venue_id") && !booking.get("venue_id").isJsonNull()
                        ? "Venue #" + value(booking, "venue_id") : "Unavailable");
                loadCourtDetails(booking);
            }
            @Override public void onError(String error) {
                showError("Could not load this booking receipt. Check your connection and try again.");
            }
        });
    }

    private void loadCourtDetails(JsonObject booking) {
        if (!booking.has("court_id") || booking.get("court_id").isJsonNull()) return;
        int courtId = booking.get("court_id").getAsInt();
        courtRepository.getCourt(courtId, new ApiCallback<JsonObject>() {
            @Override public void onSuccess(JsonObject court) {
                String name = value(court, "name");
                if (!name.isEmpty()) tvCourt.setText(name);
                if (court.has("sport_id") && !court.get("sport_id").isJsonNull()) loadSport(court.get("sport_id").getAsInt());
            }
            @Override public void onError(String error) { }
        });
        if (booking.has("venue_id") && !booking.get("venue_id").isJsonNull()) {
            courtRepository.getVenue(booking.get("venue_id").getAsInt(), new ApiCallback<JsonObject>() {
                @Override public void onSuccess(JsonObject venue) {
                    String name = value(venue, "name");
                    String address = value(venue, "address");
                    if (!name.isEmpty()) tvVenue.setText(name);
                    if (!address.isEmpty()) tvVenue.append(" · " + address);
                }
                @Override public void onError(String error) { }
            });
        }
    }

    private void loadSport(int sportId) {
        courtRepository.getSports(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray sports) {
                for (int i = 0; i < sports.size(); i++) {
                    JsonObject sport = sports.get(i).getAsJsonObject();
                    if (sport.has("id") && sport.get("id").getAsInt() == sportId) {
                        String name = value(sport, "name");
                        if (!name.isEmpty()) tvSport.setText(name);
                        return;
                    }
                }
            }
            @Override public void onError(String error) { }
        });
    }

    private boolean matchesPayment(JsonObject item) {
        return item.has("booking_id") && !item.get("booking_id").isJsonNull()
                && item.get("booking_id").getAsInt() == bookingId;
    }

    private void loadPayment() {
        paymentRepository.getPayments(new ApiCallback<JsonArray>() {
            @Override public void onSuccess(JsonArray payments) {
                for (int i = 0; i < payments.size(); i++) {
                    JsonObject candidate = payments.get(i).getAsJsonObject();
                    if (matchesPayment(candidate)) {
                        payment = candidate;
                        bindPayment(candidate);
                        return;
                    }
                }
                bindPayment(null);
            }
            @Override public void onError(String error) { bindPayment(null); }
        });
    }

    private void bindPayment(JsonObject item) {
        if (item == null) {
            tvPaymentMethod.setText("Unknown");
            tvPaymentReference.setText("Not recorded");
            tvPaymentStatus.setText("No payment record");
            tvPaymentTime.setText("Not recorded");
            return;
        }
        tvPaymentMethod.setText(CustomerUiUtils.paymentMethodLabel(value(item, "provider")));
        tvPaymentReference.setText(valueOr(item, "transaction_code", "Not recorded"));
        tvPaymentStatus.setText(valueOr(item, "status", "Unknown"));
        tvPaymentTime.setText(CustomerUiUtils.formatUtcTimestamp(value(item, "paid_at")));
    }

    private void showError(String message) {
        receiptContent.setVisibility(View.GONE);
        tvReceiptError.setText(message);
        tvReceiptError.setVisibility(View.VISIBLE);
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private static String value(JsonObject object, String key) {
        return object.has(key) && !object.get(key).isJsonNull() ? object.get(key).getAsString() : "";
    }

    private static String valueOr(JsonObject object, String key, String fallback) {
        String result = value(object, key);
        return result.isEmpty() ? fallback : result;
    }

    private static String formatTime(String value) {
        return value != null && value.length() >= 5 ? value.substring(0, 5) : "";
    }
}
