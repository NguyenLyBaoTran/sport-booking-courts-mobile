# S2 Integration Notes

## Branch and review scope

- S2 implementation branch: `feature/s2-court-service`.
- Auth source reviewed read-only from `origin/feature/s1-w1-auth-usecase`; it was not merged into this working tree.
- No S1 source files or database records were changed.

## Verified S1 Auth contract

The inspected S1 code provides:

- `POST /api/v1/auth/register` (registration always assigns USER).
- `POST /api/v1/auth/login` (JSON email/password; returns an access token and user profile).
- `GET /api/v1/users/me` (Bearer token; returns current user without password hash).
- HS256 access tokens using `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`; claims include `sub`, `role`, `iat`, and `exp`.
- Roles `USER`, `OWNER`, and `ADMIN`.

No committed OWNER/ADMIN demo credentials or role-granting workflow were found in the inspected S1 branch. S1 tests create ordinary USER accounts. The User Service has the Auth routes above. Booking and Payment services expose foundation health routes only; no Booking, QR check-in, or Payment API routes were found.

## S2 frontend integration

- Login calls Auth through the Gateway, then requests `/api/v1/users/me` before accepting the account. Only OWNER and ADMIN profiles enter their corresponding workspace; USER is rejected from the management UI.
- The access token is stored in browser `sessionStorage`, attached to API calls as Bearer authorization, and removed on logout or expired-session handling. `JWT_SECRET_KEY` is never sent to the frontend.
- Authenticated OWNER can create, update, and soft-deactivate their own Venues, Courts, and Time Slots using the existing Court API contract. The venue `owner_id` is taken from the authenticated `/users/me` profile. Court Service continues to enforce actual ownership.
- Sports mutations and all Admin Court catalogue mutations remain disabled. ADMIN authorization policy is pending confirmation.
- Demo Mode uses separate in-memory fixtures. Booking, booking completion, QR check-in, Admin user directory, Payment, and Revenue remain Demo/read-only and do not call guessed endpoints.

## Local prerequisites and limits

- The User Service, Court Service, and Gateway must be running on ports 8001, 8002, and 8000.
- Configure the same strong `JWT_SECRET_KEY` and `JWT_ALGORITHM=HS256` in User and Court services locally. The current S2 environment had no shared Auth secret and no verified real OWNER token.
- An S1-provisioned OWNER account is required to exercise Court writes. An ADMIN account is required to verify the Admin workspace using real Auth. Do not elevate a USER or create privileged test accounts by bypassing the Auth service.
- The last local Court DB check found the four schema tables but no rows. An Owner may create a Venue, but Court creation also requires an existing Sport; S2 keeps Sports writes closed pending authorization policy confirmation. Do not create Sports data by bypassing that policy.
- No end-to-end S1 login, privileged-role login, or authenticated Court mutation was run. Those paths are NOT VERIFIED until the Auth branch is integrated and valid local credentials/configuration are provided.
- Browser interactions were not automated in this environment. The API client contract is covered by `management-web/tests/api.test.js`.

## Next integration actions

1. Integrate S1 Auth through the team's normal branch/merge workflow after its review.
2. Add a server-side OWNER/ADMIN provisioning path or disposable credentials through S1; never handle privileged roles in the frontend.
3. Configure a local shared JWT secret without committing `.env`.
4. Run real Auth login/me and Owner Court CRUD through the Gateway, then verify 401/403/409/422 UI handling.
5. Agree on Booking list/detail/completion and QR check-in contracts before connecting those screens. Confirm ADMIN Court write policy before enabling it.
