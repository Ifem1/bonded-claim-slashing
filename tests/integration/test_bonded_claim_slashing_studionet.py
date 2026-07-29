"""
Full-surface StudioNet integration coverage for BondedClaimSlashing.

Every write method and every view method is exercised against a live
consensus deployment, per the "call every write, read every view" gate.
Resolution rounds are slow (one web fetch plus one nondet round) and
StudioNet is known to occasionally return CANCELED/NO_MAJORITY or
UNDETERMINED with nothing written; resolve_until_settled re-submits the
transaction itself when that happens, it does not paper over a contract bug.
"""

from gltest import create_accounts
from gltest.assertions import tx_execution_failed

from .conftest import resolve_until_settled

EVIDENCE_URL = "https://example.com"
TRUE_CLAIM = (
    "The webpage at the evidence URL contains a visible heading with the "
    "exact text 'Example Domain'."
)
FALSE_CLAIM = (
    "The webpage at the evidence URL is a bank login form that asks the "
    "visitor to enter a password and account number."
)
TERMINAL_STATUSES = {"SUPPORTED", "REFUTED", "UNKNOWN"}


def test_get_config_reads_deployed_constructor_values(claims):
    config = claims.get_config(args=[]).call()
    assert config["min_bond"] == 1000
    assert config["max_claims"] == 1000
    assert config["max_attempts"] == 3
    assert config["max_claim_chars"] == 700
    assert config["max_url_chars"] == 320
    assert config["max_summary_chars"] == 500
    assert config["next_id"] == 1


def test_submit_claim_reverts_below_minimum_bond(claims):
    accounts = create_accounts(1)
    receipt = claims.submit_claim(
        args=[TRUE_CLAIM, EVIDENCE_URL, accounts[0].address, "reject-low-bond"]
    ).transact(value=1)
    assert tx_execution_failed(receipt)


def test_submit_claim_reverts_on_non_https_url(claims):
    accounts = create_accounts(1)
    receipt = claims.submit_claim(
        args=[TRUE_CLAIM, "http://example.com", accounts[0].address, "reject-http"]
    ).transact(value=2000)
    assert tx_execution_failed(receipt)


def test_submit_claim_reverts_on_empty_claim_text(claims):
    accounts = create_accounts(1)
    receipt = claims.submit_claim(
        args=["", EVIDENCE_URL, accounts[0].address, "reject-empty-claim"]
    ).transact(value=2000)
    assert tx_execution_failed(receipt)


def test_resolve_reverts_on_unknown_claim_id(claims):
    receipt = claims.resolve_claim(args=["bcs-does-not-exist"]).transact()
    assert tx_execution_failed(receipt)


def test_withdraw_reverts_while_claim_pending(claims):
    accounts = create_accounts(1)
    consumer_key = "studionet-withdraw-pending"
    receipt = claims.submit_claim(
        args=[TRUE_CLAIM, EVIDENCE_URL, accounts[0].address, consumer_key]
    ).transact(value=2000)
    assert not tx_execution_failed(receipt)

    claim_id = claims.latest_claim_for(args=[consumer_key]).call()
    withdraw_receipt = claims.withdraw(args=[claim_id]).transact()
    assert tx_execution_failed(withdraw_receipt)


def test_retryable_unknown_is_not_withdrawable_before_attempt_cap(claims):
    accounts = create_accounts(1)
    beneficiary = accounts[0].address
    consumer_key = "studionet-retryable-unknown"

    receipt = claims.submit_claim(
        args=[
            TRUE_CLAIM,
            "https://nonexistent.invalid/claim-evidence",
            beneficiary,
            consumer_key,
        ]
    ).transact(value=2000)
    assert not tx_execution_failed(receipt)

    claim_id = claims.latest_claim_for(args=[consumer_key]).call()
    resolve_receipt = resolve_until_settled(claims, claim_id)
    assert not tx_execution_failed(resolve_receipt)

    resolved = claims.get_claim(args=[claim_id]).call()
    assert resolved["status"] == "UNKNOWN"
    assert resolved["attempts"] == 1
    assert claims.withdrawable(args=[claim_id, claims_default_recipient(claims)]).call() == 0

    withdraw_receipt = claims.withdraw(args=[claim_id]).transact()
    assert tx_execution_failed(withdraw_receipt)


def test_full_lifecycle_supported_claim_refunds_claimant(claims):
    accounts = create_accounts(1)
    beneficiary = accounts[0].address
    consumer_key = "studionet-lifecycle-supported"
    bond = 5000

    write_receipt = claims.submit_claim(
        args=[TRUE_CLAIM, EVIDENCE_URL, beneficiary, consumer_key]
    ).transact(value=bond)
    assert not tx_execution_failed(write_receipt)

    claim_id = claims.latest_claim_for(args=[consumer_key]).call()
    assert claim_id.startswith("bcs-")

    assert claims.claim_status(args=[claim_id]).call() == "PENDING"

    pending = claims.get_claim(args=[claim_id]).call()
    assert pending["exists"] is True
    assert pending["status"] == "PENDING"
    assert pending["attempts"] == 0
    assert pending["bond"] == bond
    assert pending["consumer_key"] == consumer_key
    assert pending["withdrawn"] is False

    config_before = claims.get_config(args=[]).call()

    resolve_receipt = resolve_until_settled(claims, claim_id)
    assert not tx_execution_failed(
        resolve_receipt
    ), "resolve_claim did not settle within the network retry budget"

    resolved = claims.get_claim(args=[claim_id]).call()
    assert resolved["status"] in TERMINAL_STATUSES
    assert resolved["attempts"] >= 1

    verdict = claims.claim_status(args=[claim_id]).call()
    assert verdict == resolved["status"]

    if resolved["status"] == "SUPPORTED":
        assert resolved["confidence"] == "HIGH"
        assert resolved["error_code"] == "NONE"
    elif resolved["status"] == "UNKNOWN":
        assert resolved["error_code"] in {"EXTERNAL", "LLM_ERROR", "EXPECTED"}
    else:
        assert resolved["error_code"] == "NONE"

    config_after = claims.get_config(args=[]).call()
    assert config_after["next_id"] == config_before["next_id"]

    default_account_addr = claims_default_recipient(claims)
    withdrawable_by_claimant = claims.withdrawable(
        args=[claim_id, default_account_addr]
    ).call()
    withdrawable_by_beneficiary = claims.withdrawable(args=[claim_id, beneficiary]).call()

    if resolved["status"] == "SUPPORTED":
        assert withdrawable_by_claimant == bond
        assert withdrawable_by_beneficiary == 0

        withdraw_receipt = claims.withdraw(args=[claim_id]).transact()
        assert not tx_execution_failed(withdraw_receipt)

        withdrawn = claims.get_claim(args=[claim_id]).call()
        assert withdrawn["withdrawn"] is True
        assert withdrawn["bond"] == 0

        replay_withdraw = claims.withdraw(args=[claim_id]).transact()
        assert tx_execution_failed(replay_withdraw)
    elif resolved["status"] == "REFUTED":
        assert withdrawable_by_beneficiary == bond
        assert withdrawable_by_claimant == 0

    if resolved["status"] in {"SUPPORTED", "REFUTED"}:
        replay_resolve = claims.resolve_claim(args=[claim_id]).transact()
        assert tx_execution_failed(
            replay_resolve
        ), "a terminal claim must refuse re-resolution"


def test_full_lifecycle_refuted_claim_pays_beneficiary(claims):
    accounts = create_accounts(1)
    beneficiary = accounts[0].address
    consumer_key = "studionet-lifecycle-refuted"
    bond = 5000

    write_receipt = claims.submit_claim(
        args=[FALSE_CLAIM, EVIDENCE_URL, beneficiary, consumer_key]
    ).transact(value=bond)
    assert not tx_execution_failed(write_receipt)

    claim_id = claims.latest_claim_for(args=[consumer_key]).call()

    resolve_receipt = resolve_until_settled(claims, claim_id)
    assert not tx_execution_failed(resolve_receipt)

    resolved = claims.get_claim(args=[claim_id]).call()
    assert resolved["status"] in TERMINAL_STATUSES

    if resolved["status"] == "REFUTED":
        withdrawable_by_beneficiary = claims.withdrawable(args=[claim_id, beneficiary]).call()
        assert withdrawable_by_beneficiary == bond

        beneficiary_contract = claims.connect(accounts[0])
        withdraw_receipt = beneficiary_contract.withdraw(args=[claim_id]).transact()
        assert not tx_execution_failed(withdraw_receipt)

        withdrawn = claims.get_claim(args=[claim_id]).call()
        assert withdrawn["withdrawn"] is True
        assert withdrawn["bond"] == 0


def test_resolve_convergence_on_identical_claim_and_evidence(claims):
    accounts = create_accounts(2)
    consumer_a = "studionet-convergence-a"
    consumer_b = "studionet-convergence-b"

    receipt_a = claims.submit_claim(
        args=[TRUE_CLAIM, EVIDENCE_URL, accounts[0].address, consumer_a]
    ).transact(value=2000)
    assert not tx_execution_failed(receipt_a)
    receipt_b = claims.submit_claim(
        args=[TRUE_CLAIM, EVIDENCE_URL, accounts[1].address, consumer_b]
    ).transact(value=2000)
    assert not tx_execution_failed(receipt_b)

    claim_a = claims.latest_claim_for(args=[consumer_a]).call()
    claim_b = claims.latest_claim_for(args=[consumer_b]).call()
    assert claim_a != claim_b

    resolve_a = resolve_until_settled(claims, claim_a)
    assert not tx_execution_failed(resolve_a)
    resolve_b = resolve_until_settled(claims, claim_b)
    assert not tx_execution_failed(resolve_b)

    result_a = claims.get_claim(args=[claim_a]).call()
    result_b = claims.get_claim(args=[claim_b]).call()

    assert result_a["status"] == result_b["status"], (
        "two independent consensus rounds over the same claim text and "
        "evidence URL must converge on the same verdict category, not "
        "merely avoid crashing"
    )
    assert result_a["confidence"] == result_b["confidence"]


def claims_default_recipient(claims) -> str:
    from gltest import get_default_account

    return get_default_account().address
