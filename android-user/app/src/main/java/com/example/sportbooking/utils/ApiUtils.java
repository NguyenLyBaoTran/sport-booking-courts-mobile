package com.example.sportbooking.utils;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import org.json.JSONObject;

import retrofit2.Response;

public final class ApiUtils {

    private ApiUtils() {
    }

    public static JsonArray parseAsArray(JsonElement element) {
        if (element == null) return new JsonArray();
        if (element.isJsonArray()) {
            return element.getAsJsonArray();
        }
        if (element.isJsonObject()) {
            JsonObject obj = element.getAsJsonObject();
            for (String key : new String[]{"items", "data", "courts", "venues", "sports", "time_slots", "bookings", "payments"}) {
                if (obj.has(key) && obj.get(key).isJsonArray()) {
                    return obj.get(key).getAsJsonArray();
                }
            }
            // If object has no array key but is not empty, wrap it or return empty
        }
        return new JsonArray();
    }

    public static String getErrorMessage(Response<?> response) {
        if (response.code() == 401) {
            return "Session expired. Please log in again.";
        }

        if (response.code() == 403) {
            return "You do not have permission to perform this action.";
        }

        if (response.code() == 404) {
            return "The requested data was not found.";
        }

        if (response.code() == 409) {
            return "The selected time slot is no longer available.";
        }

        if (response.errorBody() != null) {
            try {
                String errorBody = response.errorBody().string();
                JSONObject json = new JSONObject(errorBody);

                String detail = json.optString("detail", "");

                if (!detail.isEmpty()) {
                    return detail;
                }

                String message = json.optString("message", "");

                if (!message.isEmpty()) {
                    return message;
                }
            } catch (Exception ignored) {
                return "Request failed. HTTP " + response.code();
            }
        }

        return "Request failed. HTTP " + response.code();
    }

    public static String getNetworkError(Throwable throwable) {
        if (throwable == null) {
            return "Cannot connect to server.";
        }

        if (throwable.getMessage() == null) {
            return "An unexpected error occurred.";
        }

        return throwable.getMessage();
    }
}
