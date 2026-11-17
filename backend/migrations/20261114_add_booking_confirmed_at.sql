-- From the repository root, execute: mysql -u root -p sports_booking_db < backend/migrations/20261114_add_booking_confirmed_at.sql
-- Additive only: existing rows, including legacy CONFIRMED bookings, remain NULL.
ALTER TABLE bookings
    ADD COLUMN confirmed_at DATETIME NULL;
