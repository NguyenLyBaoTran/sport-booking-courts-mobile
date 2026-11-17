-- Additive migration for one logical booking associated with one or more Court Service slots.
-- Existing bookings are preserved and receive their current single slot as the anchor association.
CREATE TABLE IF NOT EXISTS booking_time_slots (
    booking_id INT NOT NULL,
    time_slot_id INT NOT NULL,
    position INT NOT NULL DEFAULT 0,
    PRIMARY KEY (booking_id, time_slot_id),
    KEY ix_booking_time_slots_time_slot_id (time_slot_id),
    CONSTRAINT fk_booking_time_slots_booking
        FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT IGNORE INTO booking_time_slots (booking_id, time_slot_id, position)
SELECT id, time_slot_id, 0
FROM bookings;
