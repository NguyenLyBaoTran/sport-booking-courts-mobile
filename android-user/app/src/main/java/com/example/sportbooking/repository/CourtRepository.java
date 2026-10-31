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

public class CourtRepository {

    private final CustomerApi api;

    public CourtRepository(Context context) {
        api = ApiClient.getCustomerApi(context);
    }

    public void getSports(ApiCallback<JsonArray> callback) {
        api.getSports().enqueue(arrayCallback(callback));
    }

    public void getVenues(ApiCallback<JsonArray> callback) {
        api.getVenues().enqueue(arrayCallback(callback));
    }

    public void getVenue(
            int venueId,
            ApiCallback<JsonObject> callback
    ) {
        api.getVenue(venueId).enqueue(objectCallback(callback));
    }

    public void searchCourts(
            Integer venueId,
            Integer sportId,
            ApiCallback<JsonArray> callback
    ) {
        api.getCourts(venueId, sportId, null)
                .enqueue(arrayCallback(callback));
    }

    public void getCourt(
            int courtId,
            ApiCallback<JsonObject> callback
    ) {
        api.getCourt(courtId).enqueue(objectCallback(callback));
    }

    public void getTimeSlots(
            int courtId,
            String date,
            ApiCallback<JsonArray> callback
    ) {
        api.getTimeSlots(courtId, date, null)
                .enqueue(arrayCallback(callback));
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
            return "Cannot connect to server.";
        }

        return throwable.getMessage();
    }
}
