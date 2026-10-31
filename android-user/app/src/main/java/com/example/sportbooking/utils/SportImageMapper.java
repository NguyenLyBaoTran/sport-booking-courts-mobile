package com.example.sportbooking.utils;

import androidx.annotation.DrawableRes;

import com.example.sportbooking.R;
import com.google.gson.JsonObject;

public final class SportImageMapper {

    private SportImageMapper() {
    }

    @DrawableRes
    public static int getPrimaryImage(JsonObject court, String sportName) {
        String name = sportName != null ? sportName : "";

        if ((court != null && court.has("sport_id"))
                && court.get("sport_id").isJsonPrimitive()) {
            int sportId = court.get("sport_id").getAsInt();
            if (sportId == 1) return R.drawable.badminton;
            if (sportId == 2) return R.drawable.football;
            if (sportId == 3) return R.drawable.basketball;
            if (sportId == 4) return R.drawable.tennis;
        }

        String lowerName = name.toLowerCase();
        if (lowerName.contains("badminton") || lowerName.contains("cau long")) {
            return R.drawable.badminton;
        }
        if (lowerName.contains("football") || lowerName.contains("soccer") || lowerName.contains("bong da")) {
            return R.drawable.football;
        }
        if (lowerName.contains("basketball") || lowerName.contains("basket")) {
            return R.drawable.basketball;
        }
        if (lowerName.contains("tennis")) {
            return R.drawable.tennis;
        }

        if (court != null && court.has("name")
                && court.get("name").isJsonPrimitive()) {
            String courtName = court.get("name").getAsString().toLowerCase();
            if (courtName.contains("badminton")) return R.drawable.badminton;
            if (courtName.contains("football") || courtName.contains("soccer")) return R.drawable.football;
            if (courtName.contains("basketball")) return R.drawable.basketball;
            if (courtName.contains("tennis")) return R.drawable.tennis;
        }

        return R.drawable.tennis_hero;
    }

    @DrawableRes
    public static int getPrimaryImage(JsonObject court) {
        return getPrimaryImage(court, null);
    }

    @DrawableRes
    public static int getSecondaryImage(JsonObject court, String sportName) {
        String name = sportName != null ? sportName : "";
        if (court != null && court.has("sport_id") && court.get("sport_id").isJsonPrimitive()) {
            int sportId = court.get("sport_id").getAsInt();
            if (sportId == 1) return R.drawable.badminton2;
            if (sportId == 2) return R.drawable.football2;
            if (sportId == 3) return R.drawable.basketball2;
            if (sportId == 4) return R.drawable.tennis2;
        }

        String lowerName = name.toLowerCase();
        if (lowerName.contains("badminton")) return R.drawable.badminton2;
        if (lowerName.contains("football") || lowerName.contains("soccer")) return R.drawable.football2;
        if (lowerName.contains("basketball")) return R.drawable.basketball2;
        if (lowerName.contains("tennis")) return R.drawable.tennis2;
        return R.drawable.tennis_hero;
    }
}
