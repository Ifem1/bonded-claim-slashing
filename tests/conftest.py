import pytest
from pathlib import Path

from gltest.direct.sdk_loader import setup_sdk_paths


setup_sdk_paths(Path("contracts/bonded_claim_slashing.py"))


def _patch_windows_fd0_unlink() -> None:
    import os
    import sys
    import tempfile

    if sys.platform != "win32":
        return

    import gltest.direct.loader as loader

    def tolerant_inject_message_to_fd0(vm):
        try:
            from genlayer.py import calldata
            from genlayer.py.types import Address
        except ImportError:
            return

        sender_addr = vm.sender
        if isinstance(sender_addr, bytes):
            sender_addr = Address(sender_addr)
        contract_addr = vm._contract_address
        if isinstance(contract_addr, bytes):
            contract_addr = Address(contract_addr)
        origin_addr = vm.origin
        if isinstance(origin_addr, bytes):
            origin_addr = Address(origin_addr)

        message_data = {
            "contract_address": contract_addr,
            "sender_address": sender_addr,
            "origin_address": origin_addr,
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        }

        encoded = calldata.encode(message_data)
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, encoded)
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
        finally:
            os.close(fd)
            try:
                os.unlink(path)
            except PermissionError:
                pass

    loader._inject_message_to_fd0 = tolerant_inject_message_to_fd0


_patch_windows_fd0_unlink()


@pytest.fixture(autouse=True)
def reset_known_contract():
    yield
    try:
        import genlayer.gl as gl

        gl.genvm_contracts.__known_contract__ = None
    except Exception:
        pass


def as_hex_address(value) -> str:
    if hasattr(value, "as_hex"):
        return value.as_hex
    from genlayer.py.types import Address

    return Address(value).as_hex


def deploy_claims(direct_deploy, **kwargs):
    args = [
        kwargs.get("min_bond", 10),
        kwargs.get("max_claims", 1000),
        kwargs.get("max_attempts", 3),
        kwargs.get("max_claim_chars", 700),
        kwargs.get("max_url_chars", 320),
        kwargs.get("max_summary_chars", 500),
    ]
    return direct_deploy("contracts/bonded_claim_slashing.py", *args)


def submit_claim(direct_vm, contract, beneficiary, value=10, consumer="consumer-a"):
    direct_vm.value = value
    try:
        return contract.submit_claim(
            "Alice shipped milestone 4 according to the public status record.",
            "https://example.com/evidence",
            as_hex_address(beneficiary),
            consumer,
        )
    finally:
        direct_vm.value = 0
