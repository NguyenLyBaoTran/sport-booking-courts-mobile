package com.example.sportbooking.repository;

import android.content.Context;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.CustomerApi;
import com.example.sportbooking.utils.ApiUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.util.UUID;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class PaymentRepository {

    private static final String PAYMENT_PREFS = "sport_booking_payment_idempotency";
    private static final String BOOKING_KEY_PREFIX = "booking_";

    private final CustomerApi api;
    private final Context context;

    public PaymentRepository(Context context) {
        this.context = context.getApplicationContext();
        api = ApiClient.getCustomerApi(context);
    }

    public void processPayment(
            int bookingId,
            String mockResult,
            ApiCallback<JsonObject> callback
    ) {
        JsonObject body = new JsonObject();
        body.addProperty("booking_id", bookingId);
        body.addProperty("mock_result", mockResult);

        String idempotencyKey = idempotencyKeyForBooking(bookingId);
        if (idempotencyKey == null) {
            callback.onError("Could not save payment retry information. Please try again.");
            return;
        }

        api.processPayment(body, idempotencyKey)
                .enqueue(objectCallback(callback));
    }

    private String idempotencyKeyForBooking(int bookingId) {
        String preferenceKey = BOOKING_KEY_PREFIX + bookingId;
        synchronized (PaymentRepository.class) {
            android.content.SharedPreferences preferences = context
                    .getSharedPreferences(PAYMENT_PREFS, Context.MODE_PRIVATE);
            String existing = preferences.getString(preferenceKey, null);
            if (existing != null && !existing.isEmpty()) return existing;

            String generated = UUID.randomUUID().toString();
            boolean saved = preferences.edit().putString(preferenceKey, generated).commit();
            return saved ? generated : null;
        }
    }

    public void getPayments(ApiCallback<JsonArray> callback) {
        api.getPayments().enqueue(arrayCallback(callback));
    }

    public void getPayment(
            int paymentId,
            ApiCallback<JsonObject> callback
    ) {
        api.getPayment(paymentId).enqueue(objectCallback(callback));
    }

    private Callback<JsonElement> arrayCallback(
            ApiCallback<JsonArray> callback
    ) {
        return new Callback<JsonElement>() {
            @Override
            public void onResponse(
                    Call<JsonElement> call,
                    Response<JsonElement> response
            ) {
                if (response.isSuccessful() && response.body() != null) {
                    JsonArray array = ApiUtils.parseAsArray(response.body());
                    callback.onSuccess(array);
                } else {
                    callback.onError(
                            ApiUtils.getErrorMessage(response)
                    );
                }
            }

            @Override
            public void onFailure(
                    Call<JsonElement> call,
                    Throwable throwable
            ) {
                callback.onError(getErrorMessage(throwable));
            }
        };
    }

    private Callback<JsonObject> objectCallback(
            ApiCallback<JsonObject> callback
    ) {
        return new Callback<JsonObject>() {
            @Override
            public void onResponse(
                    Call<JsonObject> call,
                    Response<JsonObject> response
            ) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onError(
                            ApiUtils.getErrorMessage(response)
                    );
                }
            }

            @Override
            public void onFailure(
                    Call<JsonObject> call,
                    Throwable throwable
            ) {
                callback.onError(getErrorMessage(throwable));
            }
        };
    }

    private String getErrorMessage(Throwable throwable) {
        if (throwable == null || throwable.getMessage() == null) {
            return "Cannot connect to server. Check your network or base URL.";
        }

        return throwable.getMessage();
    }
}
