"""
Exercises every write method and reads every view of the deployed
BondedClaimSlashing submission contract on StudioNet, so the explorer shows
the complete surface rather than a bare deploy.

Run with: gltest scripts/test_exercise_deployed.py -v -s --network studionet
"""

import json
import time

from gltest import get_contract_factory, get_default_account, create_accounts
from gltest.assertions import tx_execution_failed

CONTRACT_ADDRESS = "0xD8311C18d0116D394515DF301A89340aa5192410"
RESOLVE_WAIT_INTERVAL = 5000
RESOLVE_WAIT_RETRIES = 90


def resolve_until_settled(contract, claim_id, max_network_retries=10):
    last_receipt = None
    for attempt in range(max_network_retries):
        print(f"  resolve_claim attempt {attempt + 1} for {claim_id} ...")
        last_receipt = contract.resolve_claim(args=[claim_id]).transact(
            wait_interval=RESOLVE_WAIT_INTERVAL,
            wait_retries=RESOLVE_WAIT_RETRIES,
        )
        if not tx_execution_failed(last_receipt):
            return last_receipt
        print(f"  round did not settle ({last_receipt.get('status_name')}), retrying")
    return last_receipt


def test_exercise_every_write_and_view_on_deployed_contract():
    factory = get_contract_factory(contract_file_path="bonded_claim_slashing.py")
    contract = factory.build_contract(contract_address=CONTRACT_ADDRESS)

    print("== get_config (view) ==")
    config = contract.get_config(args=[]).call()
    print(json.dumps(config, indent=2))

    beneficiary_account = create_accounts(1)[0]
    beneficiary = beneficiary_account.address
    consumer_key = f"submission-exercise-{int(time.time())}"
    bond = 5000

    print("\n== submit_claim (write, payable) ==")
    claim_text = (
        "The webpage at the evidence URL contains a visible heading with the "
        "exact text 'Example Domain'."
    )
    receipt = contract.submit_claim(
        args=[claim_text, "https://example.com", beneficiary, consumer_key]
    ).transact(value=bond)
    print("tx_execution_failed:", tx_execution_failed(receipt))
    assert not tx_execution_failed(receipt)

    print("\n== latest_claim_for (view) ==")
    claim_id = contract.latest_claim_for(args=[consumer_key]).call()
    print("claim_id:", claim_id)

    print("\n== claim_status (view, PENDING) ==")
    print(contract.claim_status(args=[claim_id]).call())

    print("\n== get_claim (view, pending) ==")
    print(json.dumps(contract.get_claim(args=[claim_id]).call(), indent=2))

    print("\n== resolve_claim (write, nondet consensus round) ==")
    resolve_receipt = resolve_until_settled(contract, claim_id)
    print("tx_execution_failed:", tx_execution_failed(resolve_receipt))
    assert not tx_execution_failed(resolve_receipt)

    print("\n== get_claim (view, resolved) ==")
    resolved = contract.get_claim(args=[claim_id]).call()
    print(json.dumps(resolved, indent=2))

    default_account = get_default_account()
    print("\n== withdrawable (view, claimant) ==")
    print(contract.withdrawable(args=[claim_id, default_account.address]).call())
    print("== withdrawable (view, beneficiary) ==")
    print(contract.withdrawable(args=[claim_id, beneficiary]).call())

    if resolved["status"] in ("SUPPORTED", "REFUTED"):
        print("\n== withdraw (write) ==")
        if resolved["status"] == "SUPPORTED":
            withdraw_receipt = contract.withdraw(args=[claim_id]).transact()
        else:
            withdraw_receipt = (
                contract.connect(beneficiary_account).withdraw(args=[claim_id]).transact()
            )
        print("tx_execution_failed:", tx_execution_failed(withdraw_receipt))
        assert not tx_execution_failed(withdraw_receipt)

        print("\n== get_claim (view, after withdraw) ==")
        print(json.dumps(contract.get_claim(args=[claim_id]).call(), indent=2))
    else:
        print("\nclaim resolved UNKNOWN; no withdrawal branch exercised this run")

    print("\n== get_config (view, final) ==")
    print(json.dumps(contract.get_config(args=[]).call(), indent=2))
