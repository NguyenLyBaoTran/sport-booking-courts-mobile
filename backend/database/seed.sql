-- Local-only demo data for Sports Court Booking System.
-- No schema is created or migrated. Prepare all four service schemas first.
-- This script touches only sports_user_db and sports_court_db.
-- Booking, Payment, QR, check-in, and completion data must be created through APIs.
-- Demo password for all six accounts: password123 (Argon2id hashes generated
-- and verified with User Service's existing pwdlib password hasher).
-- Re-running inserts only missing exact demo rows; it never updates/deletes rows.

SELECT @@hostname AS mysql_host,
       DATABASE() AS current_default_schema,
       'Expected schema targets: sports_user_db, sports_court_db' AS seed_targets;
SELECT SCHEMA_NAME
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME IN ('sports_user_db', 'sports_court_db');

-- Review existing rows before execution. If a demo email/name exists with a
-- different role, owner, or inactive state, stop and resolve it manually.
SELECT id, email, role, is_active
FROM sports_user_db.users
WHERE email IN (
    'admin.demo@example.com',
    'owner1.demo@example.com',
    'owner2.demo@example.com',
    'customer1.demo@example.com',
    'customer2.demo@example.com',
    'customer3.demo@example.com'
)
ORDER BY email;
SELECT name, is_active
FROM sports_court_db.sports
WHERE name IN ('Badminton', 'Football', 'Tennis')
ORDER BY name;
SELECT v.name, u.email AS current_owner, v.is_active
FROM sports_court_db.venues AS v
LEFT JOIN sports_user_db.users AS u ON u.id = v.owner_id
WHERE v.name IN (
    'Demo Badminton Center A', 'Demo Football Center B',
    'Demo Tennis Center C', 'Demo Sports Center D'
)
ORDER BY v.name;
SELECT v.name AS venue, c.name AS court, s.name AS sport, c.is_active
FROM sports_court_db.courts AS c
JOIN sports_court_db.venues AS v ON v.id = c.venue_id
LEFT JOIN sports_court_db.sports AS s ON s.id = c.sport_id
WHERE c.name IN (
    'Badminton Court A1', 'Badminton Court A2', 'Football Court B1', 'Football Court B2',
    'Tennis Court C1', 'Tennis Court C2', 'Badminton Court D1', 'Tennis Court D2'
)
ORDER BY v.name, c.name;

-- Any conflicting demo identity or inactive named catalogue row disables all
-- inserts below. Existing valid rows are reused without changing them.
SET @demo_seed_safe =
    NOT EXISTS (
        SELECT 1 FROM sports_user_db.users
        WHERE email IN ('admin.demo@example.com', 'owner1.demo@example.com', 'owner2.demo@example.com',
                        'customer1.demo@example.com', 'customer2.demo@example.com', 'customer3.demo@example.com')
          AND (
              (email = 'admin.demo@example.com' AND role <> 'ADMIN')
              OR (email IN ('owner1.demo@example.com', 'owner2.demo@example.com') AND role <> 'OWNER')
              OR (email LIKE 'customer%.demo@example.com' AND role <> 'USER')
              OR is_active <> 1
          )
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_court_db.sports
        WHERE name IN ('Badminton', 'Football', 'Tennis') AND is_active <> 1
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_court_db.venues AS v
        LEFT JOIN sports_user_db.users AS u ON u.id = v.owner_id
        WHERE (v.name IN ('Demo Badminton Center A', 'Demo Football Center B')
               AND (COALESCE(u.email, '') <> 'owner1.demo@example.com' OR v.is_active <> 1))
           OR (v.name IN ('Demo Tennis Center C', 'Demo Sports Center D')
               AND (COALESCE(u.email, '') <> 'owner2.demo@example.com' OR v.is_active <> 1))
    )
    AND NOT EXISTS (
        SELECT 1
        FROM sports_court_db.courts AS c
        JOIN sports_court_db.venues AS v ON v.id = c.venue_id
        LEFT JOIN sports_court_db.sports AS s ON s.id = c.sport_id
        WHERE (c.name IN ('Badminton Court A1', 'Badminton Court A2')
               AND (v.name <> 'Demo Badminton Center A' OR COALESCE(s.name, '') <> 'Badminton' OR c.is_active <> 1))
           OR (c.name IN ('Football Court B1', 'Football Court B2')
               AND (v.name <> 'Demo Football Center B' OR COALESCE(s.name, '') <> 'Football' OR c.is_active <> 1))
           OR (c.name IN ('Tennis Court C1', 'Tennis Court C2')
               AND (v.name <> 'Demo Tennis Center C' OR COALESCE(s.name, '') <> 'Tennis' OR c.is_active <> 1))
           OR (c.name = 'Badminton Court D1'
               AND (v.name <> 'Demo Sports Center D' OR COALESCE(s.name, '') <> 'Badminton' OR c.is_active <> 1))
           OR (c.name = 'Tennis Court D2'
               AND (v.name <> 'Demo Sports Center D' OR COALESCE(s.name, '') <> 'Tennis' OR c.is_active <> 1))
    );
SELECT IF(@demo_seed_safe = 1, 'Preflight PASS', 'CONFLICT: no seed rows will be written') AS seed_preflight;

START TRANSACTION;

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Administrator', 'admin.demo@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$so/BzLRtmxml28hFqOIzvw$iBjpCbDhsZaZ9Boazjvj9AFwrDfJXhIIqvhqjKCWBYQ',
       NULL, 'ADMIN', 1
FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'admin.demo@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Owner One', 'owner1.demo@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$lTAYw99Uy+/RscUznCZLoA$FVmxegIw+a4JIlfhZ8uHeoVS07UsD7dTNtrqH1rnFh4',
       NULL, 'OWNER', 1
FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'owner1.demo@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Owner Two', 'owner2.demo@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'OWNER', 1
FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'owner2.demo@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Customer One', 'customer1.demo@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$RyhiVmccJYpt1jRqDgQZow$Vqo+N4e9xkVJDOSq/poUMRFoK6DoWn7IqACH66Rqz3k',
       NULL, 'USER', 1
FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer1.demo@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Customer Two', 'customer2.demo@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$L3xUq3FXOrv3DhFeXEfL3Q$s5VEUxionnyeQCNlEpbK9ksyZ3RM9gJ1WvkmK3+Eijo',
       NULL, 'USER', 1
FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer2.demo@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Customer Three', 'customer3.demo@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$Xp1bvNYJTuYMw5wVinCRMA$xKd95xHEZEOT34TG+m6EICn6gzCkfURPaJq+3CVGZq8',
       NULL, 'USER', 1
FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer3.demo@example.com');

SET @owner1_id = (
    SELECT id FROM sports_user_db.users
    WHERE email = 'owner1.demo@example.com' AND role = 'OWNER' AND is_active = 1
    LIMIT 1
);
SET @owner2_id = (
    SELECT id FROM sports_user_db.users
    WHERE email = 'owner2.demo@example.com' AND role = 'OWNER' AND is_active = 1
    LIMIT 1
);

INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Badminton', 'Demo sport', 1 FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Badminton');
INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Football', 'Demo sport', 1 FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Football');
INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Tennis', 'Demo sport', 1 FROM DUAL
WHERE @demo_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Tennis');

INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner1_id, 'Demo Badminton Center A', '1 Demo Street, District 1, Ho Chi Minh City',
       'Fictional local demo venue', '0900000001', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @demo_seed_safe = 1 AND @owner1_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Badminton Center A');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner1_id, 'Demo Football Center B', '2 Demo Street, District 1, Ho Chi Minh City',
       'Fictional local demo venue', '0900000002', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @demo_seed_safe = 1 AND @owner1_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Football Center B');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner2_id, 'Demo Tennis Center C', '3 Demo Street, District 3, Ho Chi Minh City',
       'Fictional local demo venue', '0900000003', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @demo_seed_safe = 1 AND @owner2_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Tennis Center C');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner2_id, 'Demo Sports Center D', '4 Demo Street, District 3, Ho Chi Minh City',
       'Fictional local demo venue', '0900000004', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @demo_seed_safe = 1 AND @owner2_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Sports Center D');

INSERT INTO sports_court_db.courts (venue_id, sport_id, name, description, price_per_hour, is_active)
SELECT v.id, s.id, seed.court_name, 'Fictional local demo court', seed.price, 1
FROM (
    SELECT 'Demo Badminton Center A' AS venue_name, 'owner1.demo@example.com' AS owner_email, 'Badminton' AS sport_name, 'Badminton Court A1' AS court_name, 120000.00 AS price
    UNION ALL SELECT 'Demo Badminton Center A', 'owner1.demo@example.com', 'Badminton', 'Badminton Court A2', 120000.00
    UNION ALL SELECT 'Demo Football Center B', 'owner1.demo@example.com', 'Football', 'Football Court B1', 500000.00
    UNION ALL SELECT 'Demo Football Center B', 'owner1.demo@example.com', 'Football', 'Football Court B2', 500000.00
    UNION ALL SELECT 'Demo Tennis Center C', 'owner2.demo@example.com', 'Tennis', 'Tennis Court C1', 180000.00
    UNION ALL SELECT 'Demo Tennis Center C', 'owner2.demo@example.com', 'Tennis', 'Tennis Court C2', 180000.00
    UNION ALL SELECT 'Demo Sports Center D', 'owner2.demo@example.com', 'Badminton', 'Badminton Court D1', 120000.00
    UNION ALL SELECT 'Demo Sports Center D', 'owner2.demo@example.com', 'Tennis', 'Tennis Court D2', 180000.00
) AS seed
JOIN sports_court_db.venues AS v ON v.name = seed.venue_name AND v.is_active = 1
JOIN sports_user_db.users AS owner ON owner.id = v.owner_id
    AND owner.email = seed.owner_email AND owner.role = 'OWNER' AND owner.is_active = 1
JOIN sports_court_db.sports AS s ON s.name = seed.sport_name AND s.is_active = 1
WHERE NOT EXISTS (
    SELECT 1 FROM sports_court_db.courts AS existing
    WHERE existing.venue_id = v.id AND existing.name = seed.court_name
)
  AND @demo_seed_safe = 1;

INSERT INTO sports_court_db.time_slots (court_id, slot_date, start_time, end_time, is_active)
SELECT c.id, DATE_ADD(CURRENT_DATE, INTERVAL demo_day.day_offset DAY), '09:00:00', '10:00:00', 1
FROM sports_court_db.courts AS c
JOIN sports_court_db.venues AS v ON v.id = c.venue_id
JOIN sports_user_db.users AS owner ON owner.id = v.owner_id
    AND owner.role = 'OWNER' AND owner.is_active = 1
JOIN sports_court_db.sports AS s ON s.id = c.sport_id AND s.is_active = 1
JOIN (
    SELECT 1 AS day_offset UNION ALL SELECT 2 UNION ALL SELECT 3
) AS demo_day
WHERE v.name IN (
    'Demo Badminton Center A', 'Demo Football Center B',
    'Demo Tennis Center C', 'Demo Sports Center D'
)
  AND (
      (v.name = 'Demo Badminton Center A' AND owner.email = 'owner1.demo@example.com' AND s.name = 'Badminton' AND c.name IN ('Badminton Court A1', 'Badminton Court A2'))
      OR (v.name = 'Demo Football Center B' AND owner.email = 'owner1.demo@example.com' AND s.name = 'Football' AND c.name IN ('Football Court B1', 'Football Court B2'))
      OR (v.name = 'Demo Tennis Center C' AND owner.email = 'owner2.demo@example.com' AND s.name = 'Tennis' AND c.name IN ('Tennis Court C1', 'Tennis Court C2'))
      OR (v.name = 'Demo Sports Center D' AND owner.email = 'owner2.demo@example.com' AND s.name = 'Badminton' AND c.name = 'Badminton Court D1')
      OR (v.name = 'Demo Sports Center D' AND owner.email = 'owner2.demo@example.com' AND s.name = 'Tennis' AND c.name = 'Tennis Court D2')
  )
  AND @demo_seed_safe = 1
  AND NOT EXISTS (
      SELECT 1 FROM sports_court_db.time_slots AS existing
      WHERE existing.court_id = c.id
        AND existing.slot_date = DATE_ADD(CURRENT_DATE, INTERVAL demo_day.day_offset DAY)
        AND existing.start_time = '09:00:00'
        AND existing.end_time = '10:00:00'
  );

COMMIT;

-- Verify resulting demo fixtures. Account IDs are resolved from email, not hard-coded.
SELECT id, full_name, email, role, is_active
FROM sports_user_db.users
WHERE email IN (
    'admin.demo@example.com', 'owner1.demo@example.com', 'owner2.demo@example.com',
    'customer1.demo@example.com', 'customer2.demo@example.com', 'customer3.demo@example.com'
)
ORDER BY role, email;

SELECT v.id AS venue_id, v.name AS venue, u.email AS owner_email,
       c.id AS court_id, c.name AS court, s.name AS sport,
       COUNT(ts.id) AS future_demo_slots
FROM sports_court_db.venues AS v
JOIN sports_user_db.users AS u ON u.id = v.owner_id
LEFT JOIN sports_court_db.courts AS c ON c.venue_id = v.id
LEFT JOIN sports_court_db.sports AS s ON s.id = c.sport_id
LEFT JOIN sports_court_db.time_slots AS ts
       ON ts.court_id = c.id AND ts.slot_date >= CURRENT_DATE
WHERE v.name IN (
    'Demo Badminton Center A', 'Demo Football Center B',
    'Demo Tennis Center C', 'Demo Sports Center D'
)
GROUP BY v.id, v.name, u.email, c.id, c.name, s.name
ORDER BY v.id, c.id;
