# Review Response: UNKNOWN Settlement Lifecycle

## Review Request

Joaquin requested a correction for this lifecycle edge:

> An `UNKNOWN` claim could be withdrawn and then resolved again because `resolve_claim` did not check the `withdrawn` flag. That meant the published verdict could change after the bond had already been paid.

## Fix Summary

The patched contract makes retry and settlement states mutually consistent.

Before the fix:

- `UNKNOWN` was immediately claimant-withdrawable.
- `UNKNOWN` was also retryable until `max_attempts`.
- That combination allowed a claimant to withdraw after an `UNKNOWN`, then someone could call `resolve_claim` again and publish a later verdict.

After the fix:

- Retryable `UNKNOWN` is **not withdrawable** while `attempts < max_attempts`.
- Final `UNKNOWN` becomes claimant-withdrawable only once the retry budget is exhausted.
- Any withdrawn claim is blocked from further resolution.

## Code Changes

Changed in `contracts/bonded_claim_slashing.py`:

- `resolve_claim` now rejects withdrawn claims with `claim already withdrawn`.
- `withdraw` now rejects retryable `UNKNOWN` claims with `claim retryable`.
- `withdrawable` now returns `0` for retryable `UNKNOWN`.

The terminal fund behavior is now:

- `SUPPORTED`: claimant can withdraw.
- `REFUTED`: beneficiary can withdraw.
- Retryable `UNKNOWN`: nobody can withdraw yet; anyone may retry resolution.
- Final `UNKNOWN` at `max_attempts`: claimant can withdraw.
- Withdrawn: no further resolution or withdrawal.

## Regression Tests

Added/updated direct tests:

- `test_retryable_unknown_cannot_withdraw_before_attempt_cap`
- `test_unknown_becomes_withdrawable_after_attempt_cap`
- `test_withdrawn_unknown_cannot_resolve_again`
- `test_low_confidence_supported_becomes_unknown` now asserts retryable `UNKNOWN` has `0` withdrawable amount.

Current local verification:

- `pytest tests/direct/ -q`: `29 passed`
- `genvm-lint check contracts/bonded_claim_slashing.py --json`: `ok: true`
- `genvm-lint check examples/bonded_claim_consumer.py --json`: `ok: true`

## Patched Deployment

Patched StudioNet contract:

`0x777b112C2C6c3636bab296E3e60690822F71FdD2`

Live transaction evidence:

- Deploy: `0x2b06b192c0df5b5e48ede08e7c66c87a38e48aadff323460ede87984109e07e4`
- `submit_claim`: `0x9705ad4cdeef3c1cab2a715e7d80bac56066483bd485a141fda36edb000adde5`
- `resolve_claim`: `0x5845d34f9a184b85f4a68afb4a86e420480efde407b00ae74239b02cf8dd2a65`
- `withdraw`: `0x9502e5d497c6f53df0f67e3ed4d02b59f636aa573e0ddd88b4dbf0f2881c48cd`

## Note On StudioNet Integration Rerun

The patched source was deployed and exercised on StudioNet. A full `gltest` integration rerun was also attempted on Jul 30, 2026, but the test harness failed during setup while parsing a fresh deploy receipt whose `consensus_data` field was `None`. No contract assertions ran in that attempt, so it is reported as a StudioNet/gltest receipt issue rather than a passing integration result.
