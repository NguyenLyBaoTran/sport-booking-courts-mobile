package com.example.sportbooking.api;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.Header;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface CustomerApi {

    @GET("api/v1/sports")
    Call<JsonElement> getSports();

    @GET("api/v1/venues")
    Call<JsonElement> getVenues();

    @GET("api/v1/venues/{id}")
    Call<JsonObject> getVenue(
            @Path("id") int id
    );

    @GET("api/v1/courts")
    Call<JsonElement> getCourts(
            @Query("venue_id") Integer venueId,
            @Query("sport_id") Integer sportId,
            @Query("is_active") Boolean active
    );

    @GET("api/v1/courts/{id}")
    Call<JsonObject> getCourt(
            @Path("id") int id
    );

    @GET("api/v1/time-slots")
    Call<JsonElement> getTimeSlots(
            @Query("court_id") int courtId,
            @Query("slot_date") String slotDate,
            @Query("is_active") Boolean active
    );

    @POST("api/v1/bookings")
    Call<JsonObject> createBooking(
            @Body JsonObject request
    );

    @GET("api/v1/bookings")
    Call<JsonElement> getBookings();

    @GET("api/v1/bookings/{id}")
    Call<JsonObject> getBooking(
            @Path("id") int id
    );

    @POST("api/v1/bookings/{booking_id}/cancel")
    Call<JsonObject> cancelBooking(
            @Path("booking_id") int bookingId
    );

    @POST("api/v1/payments/process")
    Call<JsonObject> processPayment(
            @Body JsonObject request,
            @Header("Idempotency-Key") String idempotencyKey
    );

    @GET("api/v1/payments")
    Call<JsonElement> getPayments();

    @GET("api/v1/payments/{id}")
    Call<JsonObject> getPayment(
            @Path("id") int id
    );
}
