# Bonded Claim Slashing Design

## Nondeterminism Budget

1. `gl.nondet.web.get(evidence_url)` fetches evidence text from the claim's registered source.
2. `gl.nondet.exec_prompt(prompt)` judges whether the evidence supports the claim.

No screenshots, multi-source reputation, or historical watching are used.

## Deterministic Surface

The contract deterministically handles:

- minimum bond enforcement
- claim ID assignment
- URL and text validation
- attempts cap
- verdict and confidence normalization
- all storage writes
- terminal-state rules
- withdrawable amount calculation
- value transfer emission

The model is asked only what the fetched evidence says. It is never asked who should receive money.

## Equivalence Principle

Validators compare whether the leader and validator outputs make the same semantic judgement about the same fetched evidence and requested claim. Outputs are equivalent if they preserve the same verdict, confidence band, material evidence summary, and abstention reason. Different wording or ordering is equivalent when the meaning is unchanged. A different verdict, date, amount, named party, status, obligation, or material fact is not equivalent.

## Terminal Funds

- `SUPPORTED`: claimant can withdraw the bond.
- `REFUTED`: beneficiary can withdraw the bond.
- `UNKNOWN`: claimant can withdraw the bond.

Funds are never intentionally left without a withdrawer in a terminal state. Value moves only through `withdraw`, after state is marked withdrawn.

## Safe Failure

Fetch failure, malformed model output, insufficient evidence, or ambiguity becomes `UNKNOWN`. `UNKNOWN` does not slash.
