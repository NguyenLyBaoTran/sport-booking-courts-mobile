-- Canonical local-development seed for Sports Court Booking.
-- Run only after all four schemas and service tables have been initialized.
-- This script writes demo Users and Court catalogue/time-slot rows only.
-- Booking, Payment, QR, check-in, and completion data must be created through APIs.
-- Newly inserted demo accounts use password123; existing password hashes are preserved.
-- Legacy demo emails are renamed in place so user IDs and linked rows remain stable.
SET NAMES utf8mb4;
USE sports_user_db;

-- Local-only demo data for Sports Court Booking System.
-- No schema is created or migrated. Prepare all four service schemas first.
-- This script touches only sports_user_db and sports_court_db.
-- Booking, Payment, QR, check-in, and completion data must be created through APIs.
-- Default password for newly inserted accounts: password123 (Argon2id generated
-- by User Service's pwdlib password hasher). Existing account password hashes
-- are preserved. Legacy email aliases are renamed in place so IDs and related
-- records stay unchanged.

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
    'admin@example.com', 'admin.demo@example.com',
    'owner1@example.com', 'owner1.demo@example.com',
    'owner2@example.com', 'owner2.demo@example.com',
    'customer1@example.com', 'customer1.demo@example.com',
    'customer2@example.com', 'customer2.demo@example.com',
    'customer3@example.com', 'customer3.demo@example.com'
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

-- Any conflicting demo identity or inactive named catalogue row disables writes.
SET @demo_seed_safe =
    NOT EXISTS (
        SELECT 1
        FROM (
            SELECT 'admin.demo@example.com' AS legacy_email, 'admin@example.com' AS email, 'Demo Administrator' AS full_name, 'ADMIN' AS role
            UNION ALL SELECT 'owner1.demo@example.com', 'owner1@example.com', 'Demo Owner One', 'OWNER'
            UNION ALL SELECT 'owner2.demo@example.com', 'owner2@example.com', 'Demo Owner Two', 'OWNER'
            UNION ALL SELECT 'customer1.demo@example.com', 'customer1@example.com', 'Demo Customer One', 'USER'
            UNION ALL SELECT 'customer2.demo@example.com', 'customer2@example.com', 'Demo Customer Two', 'USER'
            UNION ALL SELECT 'customer3.demo@example.com', 'customer3@example.com', 'Demo Customer Three', 'USER'
        ) AS expected
        JOIN sports_user_db.users AS existing ON existing.email IN (expected.legacy_email, expected.email)
        WHERE existing.full_name <> expected.full_name
           OR existing.role <> expected.role
           OR existing.is_active <> 1
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_user_db.users AS legacy
        JOIN sports_user_db.users AS standardized
          ON standardized.email = REPLACE(legacy.email, '.demo@example.com', '@example.com')
        WHERE legacy.email IN ('admin.demo@example.com', 'owner1.demo@example.com', 'owner2.demo@example.com',
                               'customer1.demo@example.com', 'customer2.demo@example.com', 'customer3.demo@example.com')
          AND legacy.id <> standardized.id
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_court_db.sports
        WHERE name IN ('Badminton', 'Football', 'Tennis') AND is_active <> 1
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_court_db.venues AS v
        LEFT JOIN sports_user_db.users AS u ON u.id = v.owner_id
        WHERE (v.name IN ('Demo Badminton Center A', 'Demo Football Center B')
               AND (COALESCE(u.email, '') NOT IN ('owner1@example.com', 'owner1.demo@example.com') OR v.is_active <> 1))
           OR (v.name IN ('Demo Tennis Center C', 'Demo Sports Center D')
               AND (COALESCE(u.email, '') NOT IN ('owner2@example.com', 'owner2.demo@example.com') OR v.is_active <> 1))
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

-- Additive local-development catalogue seed for Task 4.
-- This section is merged into the canonical seed.sql entry point.
SET NAMES utf8mb4;

SELECT @@hostname AS mysql_host,
       'Expected schema targets: sports_user_db, sports_court_db' AS seed_targets;
SELECT SCHEMA_NAME FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME IN ('sports_user_db', 'sports_court_db');

-- Review identity collisions first. Existing legacy accounts are renamed in
-- place; a collision with a separate standardized account stops the seed.
SELECT id, full_name, email, role, is_active
FROM sports_user_db.users
WHERE email IN (
    'vy.524h0040@example.com', 'vy.524h0040.demo@example.com',
    'tran.524h0130@example.com', 'tran.524h0130.demo@example.com',
    'customer4@example.com', 'customer4.demo@example.com',
    'customer5@example.com', 'customer5.demo@example.com',
    'customer6@example.com', 'customer6.demo@example.com',
    'customer7@example.com', 'customer7.demo@example.com',
    'customer8@example.com', 'customer8.demo@example.com',
    'customer9@example.com', 'customer9.demo@example.com',
    'customer10@example.com', 'customer10.demo@example.com',
    'owner3@example.com', 'owner3.demo@example.com',
    'owner4@example.com', 'owner4.demo@example.com'
)
ORDER BY email;

SELECT v.name, u.email AS owner_email, v.is_active
FROM sports_court_db.venues AS v
LEFT JOIN sports_user_db.users AS u ON u.id = v.owner_id
WHERE v.name IN ('Demo Basketball Center E', 'Demo Badminton Center F');

SET @task4_seed_safe =
    NOT EXISTS (
        SELECT 1
        FROM (
            SELECT 'vy.524h0040.demo@example.com' AS legacy_email, 'vy.524h0040@example.com' AS email, 'Võ Ngọc Thanh Vy' AS full_name, 'USER' AS role
            UNION ALL SELECT 'tran.524h0130.demo@example.com', 'tran.524h0130@example.com', 'Nguyễn Lý Bảo Trân', 'USER'
            UNION ALL SELECT 'customer4.demo@example.com', 'customer4@example.com', 'Lê Minh Khoa', 'USER'
            UNION ALL SELECT 'customer5.demo@example.com', 'customer5@example.com', 'Phạm Gia Hân', 'USER'
            UNION ALL SELECT 'customer6.demo@example.com', 'customer6@example.com', 'Trần Quốc Bảo', 'USER'
            UNION ALL SELECT 'customer7.demo@example.com', 'customer7@example.com', 'Nguyễn Thảo My', 'USER'
            UNION ALL SELECT 'customer8.demo@example.com', 'customer8@example.com', 'Võ Hoàng Nam', 'USER'
            UNION ALL SELECT 'customer9.demo@example.com', 'customer9@example.com', 'Đặng Khánh Linh', 'USER'
            UNION ALL SELECT 'customer10.demo@example.com', 'customer10@example.com', 'Bùi Đức Anh', 'USER'
            UNION ALL SELECT 'owner3.demo@example.com', 'owner3@example.com', 'Demo Owner Three', 'OWNER'
            UNION ALL SELECT 'owner4.demo@example.com', 'owner4@example.com', 'Demo Owner Four', 'OWNER'
        ) AS expected
        JOIN sports_user_db.users AS existing ON existing.email IN (expected.legacy_email, expected.email)
        WHERE existing.full_name <> expected.full_name
           OR existing.role <> expected.role
           OR existing.is_active <> 1
    )
    AND NOT EXISTS (
        SELECT 1
        FROM (
            SELECT 'vy.524h0040.demo@example.com' AS legacy_email, 'vy.524h0040@example.com' AS email
            UNION ALL SELECT 'tran.524h0130.demo@example.com', 'tran.524h0130@example.com'
            UNION ALL SELECT 'customer4.demo@example.com', 'customer4@example.com'
            UNION ALL SELECT 'customer5.demo@example.com', 'customer5@example.com'
            UNION ALL SELECT 'customer6.demo@example.com', 'customer6@example.com'
            UNION ALL SELECT 'customer7.demo@example.com', 'customer7@example.com'
            UNION ALL SELECT 'customer8.demo@example.com', 'customer8@example.com'
            UNION ALL SELECT 'customer9.demo@example.com', 'customer9@example.com'
            UNION ALL SELECT 'customer10.demo@example.com', 'customer10@example.com'
            UNION ALL SELECT 'owner3.demo@example.com', 'owner3@example.com'
            UNION ALL SELECT 'owner4.demo@example.com', 'owner4@example.com'
        ) AS aliases
        JOIN sports_user_db.users AS legacy ON legacy.email = aliases.legacy_email
        JOIN sports_user_db.users AS standardized ON standardized.email = aliases.email
        WHERE legacy.id <> standardized.id
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_court_db.venues AS v
        LEFT JOIN sports_user_db.users AS owner ON owner.id = v.owner_id
        WHERE (v.name = 'Demo Basketball Center E'
               AND (COALESCE(owner.email, '') NOT IN ('owner3@example.com', 'owner3.demo@example.com') OR v.is_active <> 1))
           OR (v.name = 'Demo Badminton Center F'
               AND (COALESCE(owner.email, '') NOT IN ('owner4@example.com', 'owner4.demo@example.com') OR v.is_active <> 1))
    )
    AND NOT EXISTS (
        SELECT 1 FROM sports_court_db.sports
        WHERE name = 'Basketball' AND is_active <> 1
    )
    AND NOT EXISTS (
        SELECT 1
        FROM sports_court_db.courts AS c
        JOIN sports_court_db.venues AS v ON v.id = c.venue_id
        LEFT JOIN sports_court_db.sports AS s ON s.id = c.sport_id
        WHERE (c.name IN ('Badminton Court A3', 'Badminton Court A4')
               AND (v.name <> 'Demo Badminton Center A' OR COALESCE(s.name, '') <> 'Badminton' OR c.is_active <> 1))
           OR (c.name IN ('Football Court B3', 'Football Court B4')
               AND (v.name <> 'Demo Football Center B' OR COALESCE(s.name, '') <> 'Football' OR c.is_active <> 1))
           OR (c.name IN ('Tennis Court C3', 'Tennis Court C4')
               AND (v.name <> 'Demo Tennis Center C' OR COALESCE(s.name, '') <> 'Tennis' OR c.is_active <> 1))
           OR (c.name IN ('Badminton Court D3', 'Tennis Court D3')
               AND (v.name <> 'Demo Sports Center D' OR c.is_active <> 1))
           OR (c.name = 'Badminton Court D3' AND COALESCE(s.name, '') <> 'Badminton')
           OR (c.name = 'Tennis Court D3' AND COALESCE(s.name, '') <> 'Tennis')
           OR (c.name IN ('Basketball Court E1', 'Basketball Court E2')
               AND (v.name <> 'Demo Basketball Center E' OR COALESCE(s.name, '') <> 'Basketball' OR c.is_active <> 1))
           OR (c.name IN ('Badminton Court F1', 'Badminton Court F2')
               AND (v.name <> 'Demo Badminton Center F' OR COALESCE(s.name, '') <> 'Badminton' OR c.is_active <> 1))
    );
SELECT IF(@task4_seed_safe = 1, 'Preflight PASS', 'CONFLICT: no Task 4 seed rows will be written') AS task4_preflight;
-- Both preflight sections run before the transaction or any data change.
SELECT IF(@demo_seed_safe = 1, 'PASS: base fixture preflight', 'FAIL: base fixture conflict') AS base_seed_preflight,
       IF(@task4_seed_safe = 1, 'PASS: Task 4 fixture preflight', 'FAIL: Task 4 fixture conflict') AS task4_seed_preflight;
SET @all_seed_safe = COALESCE(@demo_seed_safe, 0) AND COALESCE(@task4_seed_safe, 0);
CREATE TEMPORARY TABLE seed_assertion_guard (
    assertion_type VARCHAR(32) NOT NULL,
    passed TINYINT NOT NULL,
    CONSTRAINT ck_seed_preflight_pass CHECK (assertion_type <> 'preflight' OR passed = 1),
    CONSTRAINT ck_seed_verification_pass CHECK (assertion_type <> 'verification' OR passed = 1)
) ENGINE=InnoDB;
INSERT INTO seed_assertion_guard (assertion_type, passed)
VALUES ('preflight', @all_seed_safe);

-- One transaction covers both fixture sections. A SQL error before COMMIT
-- leaves transactional rows uncommitted when the mysql client exits.
START TRANSACTION;


-- Rename legacy accounts in place and apply the common seed password. IDs and
-- all venue/booking/payment relationships remain unchanged.
UPDATE sports_user_db.users
SET email = CASE email
        WHEN 'admin.demo@example.com' THEN 'admin@example.com'
        WHEN 'owner1.demo@example.com' THEN 'owner1@example.com'
        WHEN 'owner2.demo@example.com' THEN 'owner2@example.com'
        WHEN 'customer1.demo@example.com' THEN 'customer1@example.com'
        WHEN 'customer2.demo@example.com' THEN 'customer2@example.com'
        WHEN 'customer3.demo@example.com' THEN 'customer3@example.com'
        ELSE email
    END
WHERE @all_seed_safe = 1
  AND email IN ('admin.demo@example.com', 'owner1.demo@example.com',
                'owner2.demo@example.com', 'customer1.demo@example.com',
                'customer2.demo@example.com', 'customer3.demo@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Administrator', 'admin@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'ADMIN', 1
FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'admin@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Owner One', 'owner1@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'OWNER', 1
FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'owner1@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Owner Two', 'owner2@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'OWNER', 1
FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'owner2@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Customer One', 'customer1@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1
FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer1@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Customer Two', 'customer2@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1
FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer2@example.com');

INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Customer Three', 'customer3@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1
FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer3@example.com');

SET @owner1_id = (
    SELECT id FROM sports_user_db.users
    WHERE email = 'owner1@example.com' AND role = 'OWNER' AND is_active = 1
    LIMIT 1
);
SET @owner2_id = (
    SELECT id FROM sports_user_db.users
    WHERE email = 'owner2@example.com' AND role = 'OWNER' AND is_active = 1
    LIMIT 1
);

INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Badminton', 'Demo sport', 1 FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Badminton');
INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Football', 'Demo sport', 1 FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Football');
INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Tennis', 'Demo sport', 1 FROM DUAL
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Tennis');

INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner1_id, 'Demo Badminton Center A', '1 Demo Street, District 1, Ho Chi Minh City',
       'Fictional local demo venue', '0900000001', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @all_seed_safe = 1 AND @owner1_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Badminton Center A');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner1_id, 'Demo Football Center B', '2 Demo Street, District 1, Ho Chi Minh City',
       'Fictional local demo venue', '0900000002', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @all_seed_safe = 1 AND @owner1_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Football Center B');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner2_id, 'Demo Tennis Center C', '3 Demo Street, District 3, Ho Chi Minh City',
       'Fictional local demo venue', '0900000003', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @all_seed_safe = 1 AND @owner2_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Tennis Center C');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner2_id, 'Demo Sports Center D', '4 Demo Street, District 3, Ho Chi Minh City',
       'Fictional local demo venue', '0900000004', 1, CURRENT_TIMESTAMP
FROM DUAL
WHERE @all_seed_safe = 1 AND @owner2_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Sports Center D');

INSERT INTO sports_court_db.courts (venue_id, sport_id, name, description, price_per_hour, is_active)
SELECT v.id, s.id, seed.court_name, 'Fictional local demo court', seed.price, 1
FROM (
    SELECT 'Demo Badminton Center A' AS venue_name, 'owner1@example.com' AS owner_email, 'Badminton' AS sport_name, 'Badminton Court A1' AS court_name, 120000.00 AS price
    UNION ALL SELECT 'Demo Badminton Center A', 'owner1@example.com', 'Badminton', 'Badminton Court A2', 120000.00
    UNION ALL SELECT 'Demo Football Center B', 'owner1@example.com', 'Football', 'Football Court B1', 500000.00
    UNION ALL SELECT 'Demo Football Center B', 'owner1@example.com', 'Football', 'Football Court B2', 500000.00
    UNION ALL SELECT 'Demo Tennis Center C', 'owner2@example.com', 'Tennis', 'Tennis Court C1', 180000.00
    UNION ALL SELECT 'Demo Tennis Center C', 'owner2@example.com', 'Tennis', 'Tennis Court C2', 180000.00
    UNION ALL SELECT 'Demo Sports Center D', 'owner2@example.com', 'Badminton', 'Badminton Court D1', 120000.00
    UNION ALL SELECT 'Demo Sports Center D', 'owner2@example.com', 'Tennis', 'Tennis Court D2', 180000.00
) AS seed
JOIN sports_court_db.venues AS v ON v.name = seed.venue_name AND v.is_active = 1
JOIN sports_user_db.users AS owner ON owner.id = v.owner_id
    AND owner.email = seed.owner_email AND owner.role = 'OWNER' AND owner.is_active = 1
JOIN sports_court_db.sports AS s ON s.name = seed.sport_name AND s.is_active = 1
WHERE NOT EXISTS (
    SELECT 1 FROM sports_court_db.courts AS existing
    WHERE existing.venue_id = v.id AND existing.name = seed.court_name
)
  AND @all_seed_safe = 1;

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
      (v.name = 'Demo Badminton Center A' AND owner.email = 'owner1@example.com' AND s.name = 'Badminton' AND c.name IN ('Badminton Court A1', 'Badminton Court A2'))
      OR (v.name = 'Demo Football Center B' AND owner.email = 'owner1@example.com' AND s.name = 'Football' AND c.name IN ('Football Court B1', 'Football Court B2'))
      OR (v.name = 'Demo Tennis Center C' AND owner.email = 'owner2@example.com' AND s.name = 'Tennis' AND c.name IN ('Tennis Court C1', 'Tennis Court C2'))
      OR (v.name = 'Demo Sports Center D' AND owner.email = 'owner2@example.com' AND s.name = 'Badminton' AND c.name = 'Badminton Court D1')
      OR (v.name = 'Demo Sports Center D' AND owner.email = 'owner2@example.com' AND s.name = 'Tennis' AND c.name = 'Tennis Court D2')
  )
  AND @all_seed_safe = 1
  AND NOT EXISTS (
      SELECT 1 FROM sports_court_db.time_slots AS existing
      WHERE existing.court_id = c.id
        AND existing.slot_date = DATE_ADD(CURRENT_DATE, INTERVAL demo_day.day_offset DAY)
        AND existing.start_time = '09:00:00'
        AND existing.end_time = '10:00:00'
  );



-- Rename legacy seed accounts in place and set the common password, preserving
-- user IDs and all linked venue, booking, and payment rows.
UPDATE sports_user_db.users
SET email = CASE email
        WHEN 'vy.524h0040.demo@example.com' THEN 'vy.524h0040@example.com'
        WHEN 'tran.524h0130.demo@example.com' THEN 'tran.524h0130@example.com'
        WHEN 'customer4.demo@example.com' THEN 'customer4@example.com'
        WHEN 'customer5.demo@example.com' THEN 'customer5@example.com'
        WHEN 'customer6.demo@example.com' THEN 'customer6@example.com'
        WHEN 'customer7.demo@example.com' THEN 'customer7@example.com'
        WHEN 'customer8.demo@example.com' THEN 'customer8@example.com'
        WHEN 'customer9.demo@example.com' THEN 'customer9@example.com'
        WHEN 'customer10.demo@example.com' THEN 'customer10@example.com'
        WHEN 'owner3.demo@example.com' THEN 'owner3@example.com'
        WHEN 'owner4.demo@example.com' THEN 'owner4@example.com'
        ELSE email
    END
WHERE @all_seed_safe = 1
  AND email IN ('vy.524h0040.demo@example.com', 'tran.524h0130.demo@example.com',
                'customer4.demo@example.com', 'customer5.demo@example.com',
                'customer6.demo@example.com', 'customer7.demo@example.com',
                'customer8.demo@example.com', 'customer9.demo@example.com',
                'customer10.demo@example.com', 'owner3.demo@example.com',
                'owner4.demo@example.com');

-- The User model stores role USER and has no student_id column.
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Võ Ngọc Thanh Vy', 'vy.524h0040@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'vy.524h0040@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Nguyễn Lý Bảo Trân', 'tran.524h0130@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'tran.524h0130@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Lê Minh Khoa', 'customer4@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer4@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Phạm Gia Hân', 'customer5@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer5@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Trần Quốc Bảo', 'customer6@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer6@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Nguyễn Thảo My', 'customer7@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer7@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Võ Hoàng Nam', 'customer8@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer8@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Đặng Khánh Linh', 'customer9@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer9@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Bùi Đức Anh', 'customer10@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'USER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'customer10@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Owner Three', 'owner3@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'OWNER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'owner3@example.com');
INSERT INTO sports_user_db.users (full_name, email, password_hash, phone, role, is_active)
SELECT 'Demo Owner Four', 'owner4@example.com',
       '$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk',
       NULL, 'OWNER', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_user_db.users WHERE email = 'owner4@example.com');

SET @owner3_id = (SELECT id FROM sports_user_db.users WHERE email = 'owner3@example.com' AND role = 'OWNER' AND is_active = 1 LIMIT 1);
SET @owner4_id = (SELECT id FROM sports_user_db.users WHERE email = 'owner4@example.com' AND role = 'OWNER' AND is_active = 1 LIMIT 1);

INSERT INTO sports_court_db.sports (name, description, is_active)
SELECT 'Basketball', 'Demo sport', 1 FROM DUAL
WHERE @all_seed_safe = 1 AND NOT EXISTS (SELECT 1 FROM sports_court_db.sports WHERE name = 'Basketball');

INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner3_id, 'Demo Basketball Center E', '5 Demo Street, District 5, Ho Chi Minh City',
       'Fictional local demo venue', '0900000005', 1, CURRENT_TIMESTAMP
FROM DUAL WHERE @all_seed_safe = 1 AND @owner3_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Basketball Center E');
INSERT INTO sports_court_db.venues (owner_id, name, address, description, phone, is_active, created_at)
SELECT @owner4_id, 'Demo Badminton Center F', '6 Demo Street, District 7, Ho Chi Minh City',
       'Fictional local demo venue', '0900000006', 1, CURRENT_TIMESTAMP
FROM DUAL WHERE @all_seed_safe = 1 AND @owner4_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.venues WHERE name = 'Demo Badminton Center F');

INSERT INTO sports_court_db.courts (venue_id, sport_id, name, description, price_per_hour, is_active)
SELECT v.id, s.id, seed.court_name, 'Fictional local demo court', seed.price, 1
FROM (
    SELECT 'Demo Badminton Center A' AS venue_name, 'Badminton' AS sport_name, 'Badminton Court A3' AS court_name, 130000.00 AS price
    UNION ALL SELECT 'Demo Badminton Center A', 'Badminton', 'Badminton Court A4', 140000.00
    UNION ALL SELECT 'Demo Football Center B', 'Football', 'Football Court B3', 520000.00
    UNION ALL SELECT 'Demo Football Center B', 'Football', 'Football Court B4', 540000.00
    UNION ALL SELECT 'Demo Tennis Center C', 'Tennis', 'Tennis Court C3', 190000.00
    UNION ALL SELECT 'Demo Tennis Center C', 'Tennis', 'Tennis Court C4', 200000.00
    UNION ALL SELECT 'Demo Sports Center D', 'Badminton', 'Badminton Court D3', 125000.00
    UNION ALL SELECT 'Demo Sports Center D', 'Tennis', 'Tennis Court D3', 185000.00
    UNION ALL SELECT 'Demo Basketball Center E', 'Basketball', 'Basketball Court E1', 350000.00
    UNION ALL SELECT 'Demo Basketball Center E', 'Basketball', 'Basketball Court E2', 375000.00
    UNION ALL SELECT 'Demo Badminton Center F', 'Badminton', 'Badminton Court F1', 115000.00
    UNION ALL SELECT 'Demo Badminton Center F', 'Badminton', 'Badminton Court F2', 125000.00
) AS seed
JOIN sports_court_db.venues AS v ON v.name = seed.venue_name AND v.is_active = 1
JOIN sports_court_db.sports AS s ON s.name = seed.sport_name AND s.is_active = 1
WHERE @all_seed_safe = 1
  AND NOT EXISTS (SELECT 1 FROM sports_court_db.courts AS existing WHERE existing.venue_id = v.id AND existing.name = seed.court_name);

-- Expand all demo courts to multiple future mornings, afternoons, evenings,
-- and adjacent hourly slots. Unique natural keys make reruns idempotent.
INSERT INTO sports_court_db.time_slots (court_id, slot_date, start_time, end_time, is_active)
SELECT c.id, DATE_ADD(CURRENT_DATE, INTERVAL demo_day.day_offset DAY), demo_time.start_time, demo_time.end_time, 1
FROM sports_court_db.courts AS c
JOIN sports_court_db.venues AS v ON v.id = c.venue_id
JOIN (
    SELECT 1 AS day_offset UNION ALL SELECT 2 UNION ALL SELECT 3
    UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
) AS demo_day
JOIN (
    SELECT '08:00:00' AS start_time, '09:00:00' AS end_time
    UNION ALL SELECT '09:00:00', '10:00:00'
    UNION ALL SELECT '10:00:00', '11:00:00'
    UNION ALL SELECT '13:00:00', '14:00:00'
    UNION ALL SELECT '14:00:00', '15:00:00'
    UNION ALL SELECT '15:00:00', '16:00:00'
    UNION ALL SELECT '18:00:00', '19:00:00'
    UNION ALL SELECT '19:00:00', '20:00:00'
) AS demo_time
WHERE @all_seed_safe = 1
  AND v.name IN ('Demo Badminton Center A', 'Demo Football Center B', 'Demo Tennis Center C',
                 'Demo Sports Center D', 'Demo Basketball Center E', 'Demo Badminton Center F')
  AND NOT EXISTS (
      SELECT 1 FROM sports_court_db.time_slots AS existing
      WHERE existing.court_id = c.id
        AND existing.slot_date = DATE_ADD(CURRENT_DATE, INTERVAL demo_day.day_offset DAY)
        AND existing.start_time = demo_time.start_time
        AND existing.end_time = demo_time.end_time
  );

-- Verify complete fixture counts before committing. A failed check aborts the seed.
SET @seed_verify_accounts = (
    SELECT COUNT(*) = 17
       AND COALESCE(SUM(role = 'ADMIN'), 0) = 1
       AND COALESCE(SUM(role = 'OWNER'), 0) = 4
       AND COALESCE(SUM(role = 'USER'), 0) = 12
       AND COALESCE(SUM(is_active = 1), 0) = 17
    FROM sports_user_db.users
    WHERE email IN (
        'admin@example.com',
        'owner1@example.com',
        'owner2@example.com',
        'owner3@example.com',
        'owner4@example.com',
        'customer1@example.com',
        'customer2@example.com',
        'customer3@example.com',
        'customer4@example.com',
        'customer5@example.com',
        'customer6@example.com',
        'customer7@example.com',
        'customer8@example.com',
        'customer9@example.com',
        'customer10@example.com',
        'vy.524h0040@example.com',
        'tran.524h0130@example.com'
    )
);
SET @seed_verify_sports = (
    SELECT COUNT(*) = 4 FROM sports_court_db.sports
    WHERE name IN ('Badminton', 'Football', 'Tennis', 'Basketball') AND is_active = 1
);
SET @seed_verify_venues = (
    SELECT COUNT(*) = 6 FROM sports_court_db.venues
    WHERE name IN ('Demo Badminton Center A', 'Demo Football Center B',
                   'Demo Tennis Center C', 'Demo Sports Center D',
                   'Demo Basketball Center E', 'Demo Badminton Center F')
      AND is_active = 1
);
SET @seed_verify_courts = (
    SELECT COUNT(*) = 20
    FROM sports_court_db.courts AS c
    JOIN sports_court_db.venues AS v ON v.id = c.venue_id
    WHERE v.name IN ('Demo Badminton Center A', 'Demo Football Center B',
                     'Demo Tennis Center C', 'Demo Sports Center D',
                     'Demo Basketball Center E', 'Demo Badminton Center F')
      AND c.name IN (
          'Badminton Court A1', 'Badminton Court A2', 'Badminton Court A3', 'Badminton Court A4',
          'Football Court B1', 'Football Court B2', 'Football Court B3', 'Football Court B4',
          'Tennis Court C1', 'Tennis Court C2', 'Tennis Court C3', 'Tennis Court C4',
          'Badminton Court D1', 'Tennis Court D2', 'Badminton Court D3', 'Tennis Court D3',
          'Basketball Court E1', 'Basketball Court E2', 'Badminton Court F1', 'Badminton Court F2'
      )
      AND c.is_active = 1
);
SET @seed_verify_future_slots = (
    SELECT COUNT(DISTINCT c.id) = 20 AND COUNT(ts.id) >= 960
    FROM sports_court_db.courts AS c
    JOIN sports_court_db.venues AS v ON v.id = c.venue_id
    LEFT JOIN sports_court_db.time_slots AS ts
      ON ts.court_id = c.id AND ts.slot_date > CURRENT_DATE
    WHERE v.name IN ('Demo Badminton Center A', 'Demo Football Center B',
                     'Demo Tennis Center C', 'Demo Sports Center D',
                     'Demo Basketball Center E', 'Demo Badminton Center F')
      AND c.name IN (
          'Badminton Court A1', 'Badminton Court A2', 'Badminton Court A3', 'Badminton Court A4',
          'Football Court B1', 'Football Court B2', 'Football Court B3', 'Football Court B4',
          'Tennis Court C1', 'Tennis Court C2', 'Tennis Court C3', 'Tennis Court C4',
          'Badminton Court D1', 'Tennis Court D2', 'Badminton Court D3', 'Tennis Court D3',
          'Basketball Court E1', 'Basketball Court E2', 'Badminton Court F1', 'Badminton Court F2'
      )
);
SET @seed_verify_all = COALESCE(@seed_verify_accounts, 0)
    AND COALESCE(@seed_verify_sports, 0)
    AND COALESCE(@seed_verify_venues, 0)
    AND COALESCE(@seed_verify_courts, 0)
    AND COALESCE(@seed_verify_future_slots, 0);
SELECT IF(@seed_verify_accounts = 1, 'PASS: 17 demo accounts', 'FAIL: account counts/roles') AS account_verification,
       IF(@seed_verify_sports = 1, 'PASS: 4 sports', 'FAIL: sport count') AS sport_verification,
       IF(@seed_verify_venues = 1, 'PASS: 6 venues', 'FAIL: venue count') AS venue_verification,
       IF(@seed_verify_courts = 1, 'PASS: 20 courts', 'FAIL: court count') AS court_verification,
       IF(@seed_verify_future_slots = 1, 'PASS: future slots for all courts', 'FAIL: future slot coverage') AS slot_verification;
INSERT INTO seed_assertion_guard (assertion_type, passed)
VALUES ('verification', COALESCE(@seed_verify_all, 0));

COMMIT;

-- Final read-only summary after successful commit.
SELECT role, COUNT(*) AS demo_accounts
FROM sports_user_db.users
WHERE email IN (
    'admin@example.com',
        'owner1@example.com',
        'owner2@example.com',
        'owner3@example.com',
        'owner4@example.com',
        'customer1@example.com',
        'customer2@example.com',
        'customer3@example.com',
        'customer4@example.com',
        'customer5@example.com',
        'customer6@example.com',
        'customer7@example.com',
        'customer8@example.com',
        'customer9@example.com',
        'customer10@example.com',
        'vy.524h0040@example.com',
        'tran.524h0130@example.com'
)
GROUP BY role ORDER BY role;
SELECT COUNT(DISTINCT v.id) AS demo_venues,
       COUNT(DISTINCT c.id) AS demo_courts,
       COUNT(ts.id) AS future_demo_slots
FROM sports_court_db.venues AS v
LEFT JOIN sports_court_db.courts AS c ON c.venue_id = v.id
LEFT JOIN sports_court_db.time_slots AS ts
  ON ts.court_id = c.id AND ts.slot_date > CURRENT_DATE
WHERE v.name IN ('Demo Badminton Center A', 'Demo Football Center B',
                 'Demo Tennis Center C', 'Demo Sports Center D',
                 'Demo Basketball Center E', 'Demo Badminton Center F');
