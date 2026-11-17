-- Add an authoritative payment-success timestamp without rewriting existing rows.
-- Legacy PAID payments intentionally keep paid_at = NULL because their exact
-- success time cannot be reconstructed from created_at.
SET @paid_at_column_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'payments'
      AND COLUMN_NAME = 'paid_at'
);

SET @paid_at_ddl := IF(
    @paid_at_column_exists = 0,
    'ALTER TABLE payments ADD COLUMN paid_at DATETIME NULL',
    'SELECT 1'
);

PREPARE add_paid_at_column FROM @paid_at_ddl;
EXECUTE add_paid_at_column;
DEALLOCATE PREPARE add_paid_at_column;
