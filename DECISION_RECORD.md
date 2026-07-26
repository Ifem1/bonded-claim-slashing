# Decision Record: Bonded Claim Slashing

## Chosen Primitive

`BondedClaimSlashing` is a reusable GenLayer Intelligent Contract primitive for bonded claims. A claimant posts native GEN with a textual claim and an evidence URL. Consensus judges whether the fetched evidence supports the claim, and deterministic contract logic either refunds the claimant, routes the bond to a beneficiary, or returns it on `UNKNOWN`.

## Why This Is Next

This is the strongest non-visual follow-up from the original candidate set because it combines GenLayer judgement with native value. Without GenLayer, one backend, one arbitrator, or one multisig decides whether to slash the claimant. Here the bond and the judgement live in the same trust domain.

## Gate Check

- Counterfactual: without GenLayer, a centralized service controls both evidence interpretation and bond release.
- Trust problem: claimant and beneficiary may be mutually distrusting. Either can benefit from biased evidence interpretation.
- Judgement: the core question is semantic: does fetched evidence support, refute, or fail to establish the claim?
- Importability: dispute systems, registries, grant programs, reporting markets, and agent accountability contracts can import the primitive.
- Consequential decision: native GEN is refunded or slashed based on consensus output.
- Originality: this is not a frontend, not a text-only advice app, and not a format validator. It gates native value.

## Consumer Sketch

```python
@gl.contract_interface
class IBondedClaimSlashing:
    class View:
        def claim_status(self, claim_id: str) -> str: ...
        def withdrawable(self, claim_id: str, account: Address) -> u256: ...
    class Write:
        def submit_claim(self, claim: str, evidence_url: str, beneficiary: str, consumer_key: str) -> str: ...
        def resolve_claim(self, claim_id: str) -> None: ...
        def withdraw(self, claim_id: str) -> None: ...
```

The consumer does not embed web fetching, prompt design, parsing, slashing rules, or value routing.
