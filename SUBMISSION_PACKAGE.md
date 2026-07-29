# Submission Package Draft

## Title

Bonded Claim Slashing

## Notes

Bonded Claim Slashing lets a claimant back a factual claim with a real GEN bond that GenLayer consensus fetches evidence for and judges, then deterministic code refunds, slashes, or returns the bond. Review fix: retryable UNKNOWN is no longer withdrawable, and withdrawn claims cannot resolve again, so a paid claim cannot publish a later verdict. Evidence: primitive and consumer lint clean; 29 direct tests pass including the UNKNOWN settlement regression. Patched StudioNet deploy at 0x777b112C2C6c3636bab296E3e60690822F71FdD2: submit/resolve/withdraw were accepted; the live claim over https://example.com resolved SUPPORTED at HIGH confidence and emitted a 1-wei outbound withdraw message.

## Character Count

The notes paragraph is 694 characters, counted programmatically with PowerShell `.Length`.

## Evidence Links

- GitHub repo: https://github.com/Ifem1/bonded-claim-slashing
- Explorer contract page: https://explorer-studio.genlayer.com/contracts/0x777b112C2C6c3636bab296E3e60690822F71FdD2
- Studio import: network `studionet`, contract address `0x777b112C2C6c3636bab296E3e60690822F71FdD2`

## Source Files

- Contract: `contracts/bonded_claim_slashing.py`
- Consumer example: `examples/bonded_claim_consumer.py`
- Direct tests: `tests/direct/test_bonded_claim_slashing.py` (29 tests)
- StudioNet integration tests: `tests/integration/test_bonded_claim_slashing_studionet.py` (10 tests; Jul 30 rerun was blocked by a StudioNet/gltest deploy receipt parsing error before assertions)
- Live-address exercise script: `scripts/test_exercise_deployed.py`
- Decision record: `DECISION_RECORD.md`
- Design: `PHASE2_DESIGN.md`

## Deployments

- Patched canonical deploy: `0x777b112C2C6c3636bab296E3e60690822F71FdD2`
- Deploy tx: `0x2b06b192c0df5b5e48ede08e7c66c87a38e48aadff323460ede87984109e07e4`
- `submit_claim`: `0x9705ad4cdeef3c1cab2a715e7d80bac56066483bd485a141fda36edb000adde5`
- `resolve_claim`: `0x5845d34f9a184b85f4a68afb4a86e420480efde407b00ae74239b02cf8dd2a65`
- `withdraw`: `0x9502e5d497c6f53df0f67e3ed4d02b59f636aa573e0ddd88b4dbf0f2881c48cd`
- Superseded deploys: `0xe91E76dF3d62430Eae9263C0F3c430F8522A8109`, `0xD8311C18d0116D394515DF301A89340aa5192410`

## Local Verification

- `pytest tests/direct/ -q`: `29 passed`
- `gltest tests/integration/ -v -s --network studionet`: blocked at setup by StudioNet/gltest deploy receipt parsing (`consensus_data: None`) on Jul 30, 2026
- `genvm-lint check contracts/bonded_claim_slashing.py --json`: `ok: true`
- `genvm-lint check examples/bonded_claim_consumer.py --json`: `ok: true`

## Git Hygiene

This folder is its own git repository, pushed to the public GitHub repo linked above. Single clean commit, no AI/agent co-author trailers (verified with `git log -1 --format='%B' | grep -i "co-authored\|claude\|generated with"`, which returns nothing).
