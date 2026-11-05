package com.example.sportbooking.repository;

import android.content.Context;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.CustomerApi;
import com.example.sportbooking.utils.ApiUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class BookingRepository {

    private final CustomerApi api;

    public BookingRepository(Context context) {
        api = ApiClient.getCustomerApi(context);
    }

    public void createBooking(
            int timeSlotId,
            ApiCallback<JsonObject> callback
    ) {
        JsonObject body = new JsonObject();
        body.addProperty("time_slot_id", timeSlotId);

        api.createBooking(body).enqueue(objectCallback(callback));
    }

    public void getBookings(ApiCallback<JsonArray> callback) {
        api.getBookings().enqueue(arrayCallback(callback));
    }

    public void getBooking(
            int bookingId,
            ApiCallback<JsonObject> callback
    ) {
        api.getBooking(bookingId).enqueue(objectCallback(callback));
    }

    public void cancelBooking(
            int bookingId,
            ApiCallback<JsonObject> callback
    ) {
        api.cancelBooking(bookingId).enqueue(objectCallback(callback));
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
                }
                else {
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
            return "Cannot connect to server.";
        }

        return throwable.getMessage();
    }
}
