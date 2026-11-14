package com.example.sportbooking;

import org.junit.Test;

import com.google.gson.JsonObject;

import java.util.Arrays;

import static org.junit.Assert.*;

/**
 * Example local unit test, which will execute on the development machine (host).
 *
 * @see <a href="http://d.android.com/tools/testing">Testing documentation</a>
 */
public class ExampleUnitTest {
    @Test
    public void addition_isCorrect() {
        assertEquals(4, 2 + 2);
    }

    @Test
    public void availableSlotsAreSelectableButHeldAndBookedSlotsAreNot() {
        assertTrue(SelectDateTimeActivity.isSelectable(slot(1, 4, "2026-12-01", "08:00:00", "09:00:00", "AVAILABLE", true)));
        assertFalse(SelectDateTimeActivity.isSelectable(slot(2, 4, "2026-12-01", "09:00:00", "10:00:00", "HELD", false)));
        assertFalse(SelectDateTimeActivity.isSelectable(slot(3, 4, "2026-12-01", "10:00:00", "11:00:00", "BOOKED", false)));
    }

    @Test
    public void selectedSlotsMustBeConsecutiveUniqueAndOnOneCourtAndDate() {
        JsonObject first = slot(1, 4, "2026-12-01", "08:00:00", "09:00:00", "AVAILABLE", true);
        JsonObject second = slot(2, 4, "2026-12-01", "09:00:00", "10:00:00", "AVAILABLE", true);
        JsonObject third = slot(3, 4, "2026-12-01", "10:00:00", "11:00:00", "AVAILABLE", true);
        assertTrue(SelectDateTimeActivity.areContiguous(Arrays.asList(first, second), 4, "2026-12-01"));
        assertTrue(SelectDateTimeActivity.areContiguous(Arrays.asList(first, second, third), 4, "2026-12-01"));
        assertFalse(SelectDateTimeActivity.areContiguous(Arrays.asList(first, third), 4, "2026-12-01"));
        assertFalse(SelectDateTimeActivity.areContiguous(Arrays.asList(first, first), 4, "2026-12-01"));
        JsonObject otherCourt = slot(4, 5, "2026-12-01", "09:00:00", "10:00:00", "AVAILABLE", true);
        JsonObject otherDate = slot(5, 4, "2026-12-02", "09:00:00", "10:00:00", "AVAILABLE", true);
        assertFalse(SelectDateTimeActivity.areContiguous(Arrays.asList(first, otherCourt), 4, "2026-12-01"));
        assertFalse(SelectDateTimeActivity.areContiguous(Arrays.asList(first, otherDate), 4, "2026-12-01"));
    }

    @Test
    public void customerSlotTimeFormattingOmitsSeconds() {
        assertEquals("08:00", SelectDateTimeActivity.formatTime("08:00:00"));
        assertEquals("09:30", SelectDateTimeActivity.formatTime("09:30:59"));
    }

    private static JsonObject slot(int id, int courtId, String date, String start, String end, String status, boolean selectable) {
        JsonObject value = new JsonObject();
        value.addProperty("id", id);
        value.addProperty("court_id", courtId);
        value.addProperty("slot_date", date);
        value.addProperty("start_time", start);
        value.addProperty("end_time", end);
        value.addProperty("reservation_status", status);
        value.addProperty("is_active", true);
        value.addProperty("is_selectable", selectable);
        return value;
    }
}
