-- Apply only to a disposable/local sports_court_db after backing up any data.
-- This file is intentionally not executed by S2 integration preparation.
ALTER TABLE time_slots
    ADD COLUMN reservation_status VARCHAR(10) NOT NULL DEFAULT 'AVAILABLE',
    ADD COLUMN reservation_booking_id INT NULL,
    ADD COLUMN reservation_expires_at DATETIME NULL,
    ADD INDEX ix_time_slots_reservation_expiry (reservation_status, reservation_expires_at);
