# Submission Package Draft

## Title

Bonded Claim Slashing

## Notes

Bonded Claim Slashing lets a claimant back a factual claim with a real GEN bond that GenLayer consensus fetches evidence for and judges, then deterministic contract logic refunds the claimant, slashes the bond to a named beneficiary, or returns it on UNKNOWN. The model only reads fetched evidence and never decides who gets paid: bond minimums, URL/text validation, confidence banding, terminal-state rules, withdrawer selection, and transfer ordering are all deterministic. Confidence below HIGH is deterministically downgraded to UNKNOWN before storage, so a shaky guess cannot slash a bond. Evidence: primitive and consumer lint clean; 26 direct tests pass; 9 StudioNet integration tests pass covering every write, every view, both payout paths, and a strict convergence check. StudioNet deploy at 0xD8311C18d0116D394515DF301A89340aa5192410: a live claim over https://example.com resolved SUPPORTED at HIGH confidence and withdrew correctly on the first attempt.

## Character Count

The notes paragraph is 966 characters, counted programmatically with Python `len()`.

## Evidence Links

- GitHub repo: (to be created — see Git Hygiene below)
- Explorer contract page: https://explorer-studio.genlayer.com/contracts/0xD8311C18d0116D394515DF301A89340aa5192410
- Studio import: network `studionet`, contract address `0xD8311C18d0116D394515DF301A89340aa5192410`

## Source Files

- Contract: `contracts/bonded_claim_slashing.py`
- Consumer example: `examples/bonded_claim_consumer.py`
- Direct tests: `tests/direct/test_bonded_claim_slashing.py` (26 tests)
- StudioNet integration tests: `tests/integration/test_bonded_claim_slashing_studionet.py` (9 tests)
- Live-address exercise script: `scripts/test_exercise_deployed.py`
- Decision record: `DECISION_RECORD.md`
- Design: `PHASE2_DESIGN.md`

## Prior deployment superseded

An earlier deploy at `0xe91E76dF3d62430Eae9263C0F3c430F8522A8109` also exercised `submit_claim` / `resolve_claim` / `withdraw` successfully but predates the StudioNet integration test suite. `0xD8311C18d0116D394515DF301A89340aa5192410` is the canonical submission address going forward, with the fuller evidence trail (9 passing integration tests plus the standalone exercise script) documented in the README.

## Local Verification

- `pytest tests/direct/ -q`: `26 passed`
- `gltest tests/integration/ -v -s --network studionet`: `9 passed` (372.90s)
- `genvm-lint check contracts/bonded_claim_slashing.py --json`: `ok: true`
- `genvm-lint check examples/bonded_claim_consumer.py --json`: `ok: true`

## Git Hygiene

This folder is not yet its own git repository. Before submission, initialize it (`git init`), commit with meaningful messages, push to a public GitHub repo, and update the Evidence Links section above with the real URL. No AI/agent co-author trailers.
