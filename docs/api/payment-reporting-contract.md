# Payment Reporting API Contract

All public paths are relative to `/api/v1` and pass through the existing Gateway
`/payments` route to Payment Service.

## Report

`GET /api/v1/payments/report`

Roles are taken from the verified bearer token:

- `OWNER`: payments are included only when Booking Service's internal lookup
  says the associated booking's `owner_id` equals JWT `sub`.
- `ADMIN`: system-wide report.
- `USER`: `403`.

The client cannot supply an Owner ID to select report scope.

The existing customer `GET /api/v1/payments` and `GET /api/v1/payments/{id}`
responses add nullable `paid_at`; those endpoints remain customer-only.

Optional query parameters:

| Name | Values | Default |
|---|---|---|
| `date_from` | Inclusive ISO date (`YYYY-MM-DD`) | omitted |
| `date_to` | Inclusive ISO date (`YYYY-MM-DD`) | omitted |
| `timezone` | IANA time zone used for date filters and grouping | `UTC` |
| `group_by` | `day`, `month` | `day` |
| `page` | Positive integer | `1` |
| `page_size` | `1`–`100` | `25` |
| `sort` | `asc`, `desc` by payment date | `desc` |

For `PAID`, the report uses `paid_at` as payment date. For `PENDING` and
`FAILED`, the date filter/history uses `created_at` (attempt creation date).
The optional `timezone` applies to calendar-day boundaries and revenue grouping;
it defaults to UTC. Management Web sends `Asia/Ho_Chi_Minh` so a selected
Vietnam calendar day includes its complete local day, including transactions
near midnight. Timestamps in responses remain UTC.
Only `PAID` amounts contribute to revenue. Each successful booking is unique in
Payment Service through the existing unique `successful_booking_id` constraint.
Cancelled bookings remain paid unless a separately recorded refund exists;
there is no refund field/status in the current model.

`paid_at` is assigned using Payment Service UTC server time in the same database
transaction as the first transition to `PAID`. Existing `PAID` rows retain
`paid_at = NULL`: they are included in unfiltered all-time revenue, excluded
from dated chart buckets and date-filtered totals, and included in the separate
`undated_successful_payments` / `undated_successful_amount` values. Their
`created_at` is never used to infer a success date.

Response shape:

```json
{
  "date_from": null,
  "date_to": null,
  "timezone": "UTC",
  "group_by": "day",
  "sort": "desc",
  "summary": {
    "total_revenue": "0.00",
    "successful_payments": 0,
    "pending_payments": 0,
    "failed_payments": 0,
    "total_transactions": 0,
    "undated_successful_payments": 0,
    "undated_successful_amount": "0.00"
  },
  "revenue_series": [],
  "transactions": {"items": [], "total": 0, "page": 1, "page_size": 25}
}
```

Transactions expose `payment_id`, `booking_id`, `provider`, `booking_status`,
`venue_id`, `court_id`, `status`, `amount`, `transaction_code`, `payment_date`,
and `created_at`. Customer identity and QR token are not included.

## Internal Booking ownership lookup

Payment Service calls `POST /api/v1/internal/bookings/payment-report-context`
directly at Booking Service with `X-Internal-Token` and a body of 1–500 unique
IDs:

```json
{"booking_ids": [42, 43]}
```

The response contains only each found booking's `booking_id`, `owner_id`,
`venue_id`, `court_id`, and `status`. The endpoint is not mapped by Gateway and
does not accept a caller-selected owner scope.

## Applying the additive migration

From the repository root in Command Prompt (the command is also callable from
PowerShell via `cmd /c`), after confirming the configured Payment database:

```cmd
mysql -u root -p sports_payment_db < backend/migrations/20261115_add_payment_paid_at.sql
```

This migration only adds nullable `payments.paid_at`; it does not backfill or
delete records. It can be rerun safely and does not change existing constraints.
