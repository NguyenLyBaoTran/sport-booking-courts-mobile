package com.example.sportbooking.utils;

import java.text.NumberFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

public final class CustomerUiUtils {
    private CustomerUiUtils() {}

    public static String paymentMethodLabel(String provider) {
        if (provider == null || provider.trim().isEmpty()) return "Unknown";
        switch (provider.trim().toUpperCase(Locale.ROOT)) {
            case "MOCK": return "Mock";
            case "VNPAY": return "VNPay";
            case "MOMO": return "MoMo";
            case "ZALOPAY": return "ZaloPay";
            default: return provider.trim();
        }
    }

    public static String durationLabel(String start, String end) {
        int startMinutes = minutes(start);
        int endMinutes = minutes(end);
        if (startMinutes < 0 || endMinutes <= startMinutes) return "Unavailable";
        int duration = endMinutes - startMinutes;
        int hours = duration / 60;
        int minutes = duration % 60;
        if (hours > 0 && minutes > 0) return hours + " hr " + minutes + " min";
        if (hours > 0) return hours + (hours == 1 ? " hour" : " hours");
        return minutes + " min";
    }

    public static String timeSlotLabel(String start, String end) {
        String left = shortTime(start);
        String right = shortTime(end);
        return left.isEmpty() || right.isEmpty() ? "Time unavailable" : left + " - " + right;
    }

    public static boolean isCompletedBooking(String status) {
        return status != null && "COMPLETED".equalsIgnoreCase(status.trim());
    }

    public static boolean matchesCourtFilters(String query, String name, String description,
                                               String venueInfo, String sportName,
                                               int venueId, Integer selectedVenueId,
                                               int sportId, Integer selectedSportId) {
        if (selectedVenueId != null && venueId != selectedVenueId) return false;
        if (selectedSportId != null && sportId != selectedSportId) return false;
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        return needle.isEmpty()
                || contains(name, needle)
                || contains(description, needle)
                || contains(venueInfo, needle)
                || contains(sportName, needle);
    }

    public static String formatAmount(String amount) {
        try {
            return NumberFormat.getNumberInstance(new Locale("vi", "VN"))
                    .format(Double.parseDouble(amount));
        } catch (Exception ignored) {
            return amount == null ? "Unavailable" : amount;
        }
    }

    public static String formatBookingDate(String date) {
        if (date == null || !date.matches("\\d{4}-\\d{2}-\\d{2}")) return date == null ? "Unavailable" : date;
        try {
            Date parsed = new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).parse(date);
            return new SimpleDateFormat("dd/MM/yyyy", Locale.ROOT).format(parsed);
        } catch (ParseException ignored) {
            return date;
        }
    }

    public static String formatUtcTimestamp(String value) {
        if (value == null || value.trim().isEmpty()) return "Not recorded";
        String[] patterns = {"yyyy-MM-dd'T'HH:mm:ss.SSSX", "yyyy-MM-dd'T'HH:mm:ssX"};
        for (String pattern : patterns) {
            SimpleDateFormat parser = new SimpleDateFormat(pattern, Locale.ROOT);
            parser.setTimeZone(TimeZone.getTimeZone("UTC"));
            parser.setLenient(false);
            try {
                Date parsed = parser.parse(value);
                SimpleDateFormat output = new SimpleDateFormat("dd/MM/yyyy HH:mm 'UTC'", Locale.ROOT);
                output.setTimeZone(TimeZone.getTimeZone("UTC"));
                return output.format(parsed);
            } catch (ParseException ignored) { }
        }
        return value;
    }

    private static int minutes(String value) {
        if (value == null || value.length() < 5 || value.charAt(2) != ':') return -1;
        try {
            int hour = Integer.parseInt(value.substring(0, 2));
            int minute = Integer.parseInt(value.substring(3, 5));
            if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return -1;
            return hour * 60 + minute;
        } catch (NumberFormatException ignored) {
            return -1;
        }
    }

    private static String shortTime(String value) {
        return value == null || value.length() < 5 ? "" : value.substring(0, 5);
    }

    private static boolean contains(String value, String needle) {
        return value != null && value.toLowerCase(Locale.ROOT).contains(needle);
    }
}
