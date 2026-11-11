package com.example.sportbooking.utils;

import androidx.annotation.DrawableRes;

import com.example.sportbooking.R;
import com.google.gson.JsonObject;

public final class SportImageMapper {

    private SportImageMapper() {
    }

    @DrawableRes
    public static int getSportIcon(String sportName) {
        String lower = sportName != null ? sportName.toLowerCase() : "";
        if (lower.contains("badminton") || lower.contains("cau long")) {
            return R.drawable.badminton_icon;
        }
        if (lower.contains("football") || lower.contains("soccer") || lower.contains("bong da")) {
            return R.drawable.football_icon;
        }
        if (lower.contains("pickle") || lower.contains("pickleball")) {
            return R.drawable.pickleball_icon;
        }
        if (lower.contains("basketball") || lower.contains("basket")) {
            return R.drawable.ic_basketball;
        }
        if (lower.contains("tennis")) {
            return R.drawable.ic_tennis;
        }
        return R.drawable.ic_sport;
    }

    @DrawableRes
    public static int getPrimaryImage(JsonObject court, String sportName) {
        String name = sportName != null ? sportName : "";

        String lowerName = name.toLowerCase();
        if (lowerName.contains("pickle") || lowerName.contains("pickleball")) {
            return R.drawable.pickleball;
        }
        if (lowerName.contains("badminton") || lowerName.contains("cau long")) {
            return R.drawable.badminton;
        }
        if (lowerName.contains("football") || lowerName.contains("soccer") || lowerName.contains("bong da")) {
            return R.drawable.football;
        }

        if (court != null && court.has("name")
                && court.get("name").isJsonPrimitive()) {
            String courtName = court.get("name").getAsString().toLowerCase();
            if (courtName.contains("pickle") || courtName.contains("pickleball")) return R.drawable.pickleball;
            if (courtName.contains("badminton")) return R.drawable.badminton;
            if (courtName.contains("football") || courtName.contains("soccer")) return R.drawable.football;
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
        String lowerName = name.toLowerCase();
        if (lowerName.contains("pickle") || lowerName.contains("pickleball")) return R.drawable.pickleball2;
        if (lowerName.contains("badminton")) return R.drawable.badminton2;
        if (lowerName.contains("football") || lowerName.contains("soccer")) return R.drawable.football2;
        return R.drawable.tennis_hero;
    }
}
