import pytest

from gltest import get_contract_factory
from gltest.assertions import tx_execution_failed

RESOLVE_WAIT_INTERVAL = 5000
RESOLVE_WAIT_RETRIES = 90


@pytest.fixture(scope="module")
def claims_factory():
    return get_contract_factory(contract_file_path="bonded_claim_slashing.py")


@pytest.fixture(scope="module")
def claims(claims_factory):
    return claims_factory.deploy(
        args=[1000, 1000, 3, 700, 320, 500],
        wait_interval=RESOLVE_WAIT_INTERVAL,
        wait_retries=RESOLVE_WAIT_RETRIES,
    )


def resolve_until_settled(contract, claim_id: str, max_network_retries: int = 8):
    """
    Retries the resolve_claim() transaction itself, not the contract's own
    attempt counter. StudioNet consensus rounds can return CANCELED/NO_MAJORITY
    or UNDETERMINED with nothing written and the transaction reported as
    failed; that is documented, expected flakiness, not a contract bug, so
    this loop re-submits until a round actually lands or the retry budget is
    spent.
    """
    last_receipt = None
    for _ in range(max_network_retries):
        last_receipt = contract.resolve_claim(args=[claim_id]).transact(
            wait_interval=RESOLVE_WAIT_INTERVAL,
            wait_retries=RESOLVE_WAIT_RETRIES,
        )
        if not tx_execution_failed(last_receipt):
            return last_receipt
    return last_receipt
