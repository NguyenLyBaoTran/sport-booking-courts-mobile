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

    private final CustomerApi api;

    public PaymentRepository(Context context) {
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

        String idempotencyKey = UUID.randomUUID().toString();

        api.processPayment(body, idempotencyKey)
                .enqueue(objectCallback(callback));
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
                            "Request failed. HTTP " + response.code()
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
                            "Request failed. HTTP " + response.code()
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
