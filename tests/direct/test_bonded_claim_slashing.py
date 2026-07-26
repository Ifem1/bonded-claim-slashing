from tests.conftest import as_hex_address, deploy_claims, submit_claim


STATUS_PENDING = "PENDING"
STATUS_SUPPORTED = "SUPPORTED"
STATUS_REFUTED = "REFUTED"
STATUS_UNKNOWN = "UNKNOWN"


def test_submit_claim_requires_minimum_bond(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy, min_bond=10)
    direct_vm.value = 9

    with direct_vm.expect_revert("bond below minimum"):
        contract.submit_claim(
            "Alice shipped milestone 4 according to the public status record.",
            "https://example.com/evidence",
            as_hex_address(direct_bob),
            "consumer-a",
        )
    direct_vm.value = 0


def test_submit_claim_stores_pending_bonded_record(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy, min_bond=10)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=15)

    record = contract.get_claim(claim_id)
    assert claim_id == "bcs-1"
    assert record["status"] == STATUS_PENDING
    assert record["bond"] == 15
    assert record["beneficiary"] == as_hex_address(direct_bob)
    assert contract.latest_claim_for("consumer-a") == claim_id


def test_unknown_claim_reads_fail_closed(direct_deploy):
    contract = deploy_claims(direct_deploy)

    assert contract.claim_status("missing") == STATUS_UNKNOWN
    assert contract.withdrawable("missing", "0x0000000000000000000000000000000000000000") == 0
    assert contract.get_claim("missing")["exists"] is False


def test_invalid_evidence_url_reverts(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy)
    direct_vm.value = 10

    with direct_vm.expect_revert("evidence_url must be https"):
        contract.submit_claim(
            "Alice shipped milestone 4 according to the public status record.",
            "http://example.com/evidence",
            as_hex_address(direct_bob),
            "consumer-a",
        )
    direct_vm.value = 0


def test_empty_claim_reverts(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy)
    direct_vm.value = 10

    with direct_vm.expect_revert("claim is required"):
        contract.submit_claim("", "https://example.com/evidence", as_hex_address(direct_bob), "")
    direct_vm.value = 0


def test_claim_cap_is_enforced(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy, max_claims=1)
    submit_claim(direct_vm, contract, direct_bob, value=10)

    direct_vm.value = 10
    with direct_vm.expect_revert("claim cap reached"):
        contract.submit_claim(
            "Alice shipped milestone 5 according to the public status record.",
            "https://example.com/evidence",
            as_hex_address(direct_bob),
            "consumer-a",
        )
    direct_vm.value = 0


def test_resolve_supported_refunds_claimant(direct_vm, direct_deploy, direct_bob, direct_owner):
    direct_vm.mock_web(r"example\.com", {"status": 200, "body": "Milestone 4 shipped by Alice."})
    direct_vm.mock_llm(
        r"Milestone 4 shipped",
        '{"verdict":"SUPPORTED","confidence":"HIGH","evidence_summary":"Evidence says milestone 4 shipped.","error_code":"NONE"}',
    )
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    contract.resolve_claim(claim_id)

    assert contract.claim_status(claim_id) == STATUS_SUPPORTED
    assert contract.withdrawable(claim_id, as_hex_address(direct_owner)) == 10
    assert contract.withdrawable(claim_id, as_hex_address(direct_bob)) == 0


def test_resolve_refuted_slashes_to_beneficiary(direct_vm, direct_deploy, direct_bob):
    direct_vm.mock_web(r"example\.com", {"status": 200, "body": "Milestone 4 was not delivered."})
    direct_vm.mock_llm(
        r"Milestone 4 was not delivered",
        '{"verdict":"REFUTED","confidence":"HIGH","evidence_summary":"Evidence says milestone 4 was not delivered.","error_code":"NONE"}',
    )
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    contract.resolve_claim(claim_id)

    assert contract.claim_status(claim_id) == STATUS_REFUTED
    assert contract.withdrawable(claim_id, as_hex_address(direct_bob)) == 10


def test_low_confidence_supported_becomes_unknown(direct_vm, direct_deploy, direct_bob, direct_owner):
    direct_vm.mock_web(r"example\.com", {"status": 200, "body": "Maybe shipped."})
    direct_vm.mock_llm(
        r"Maybe shipped",
        '{"verdict":"SUPPORTED","confidence":"MEDIUM","evidence_summary":"Maybe shipped.","error_code":"NONE"}',
    )
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    contract.resolve_claim(claim_id)

    assert contract.claim_status(claim_id) == STATUS_UNKNOWN
    assert contract.withdrawable(claim_id, as_hex_address(direct_owner)) == 10


def test_malformed_model_output_becomes_unknown(direct_vm, direct_deploy, direct_bob):
    direct_vm.mock_web(r"example\.com", {"status": 200, "body": "Evidence body"})
    direct_vm.mock_llm(r"Evidence body", "not json")
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    contract.resolve_claim(claim_id)

    record = contract.get_claim(claim_id)
    assert record["status"] == STATUS_UNKNOWN
    assert record["error_code"] == "LLM_ERROR"


def test_external_fetch_failure_becomes_unknown(direct_vm, direct_deploy, direct_bob):
    direct_vm.mock_web(r"example\.com", {"status": 500, "body": "down"})
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    contract.resolve_claim(claim_id)

    record = contract.get_claim(claim_id)
    assert record["status"] == STATUS_UNKNOWN
    assert record["error_code"] == "EXTERNAL"


def test_unknown_can_retry_until_attempt_cap(direct_vm, direct_deploy, direct_bob):
    direct_vm.mock_web(r"example\.com", {"status": 500, "body": "down"})
    contract = deploy_claims(direct_deploy, max_attempts=2)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    contract.resolve_claim(claim_id)
    contract.resolve_claim(claim_id)

    assert contract.get_claim(claim_id)["attempts"] == 2
    with direct_vm.expect_revert("attempt cap reached"):
        contract.resolve_claim(claim_id)


def test_pending_claim_cannot_withdraw(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)

    with direct_vm.expect_revert("claim pending"):
        contract.withdraw(claim_id)


def test_wrong_party_cannot_withdraw_supported_claim(direct_vm, direct_deploy, direct_bob):
    direct_vm.mock_web(r"example\.com", {"status": 200, "body": "Milestone 4 shipped by Alice."})
    direct_vm.mock_llm(
        r"Milestone 4 shipped",
        '{"verdict":"SUPPORTED","confidence":"HIGH","evidence_summary":"Evidence says shipped.","error_code":"NONE"}',
    )
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)
    contract.resolve_claim(claim_id)

    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("not withdrawer"):
            contract.withdraw(claim_id)


def test_withdraw_marks_state_before_value_leaves(direct_vm, direct_deploy, direct_bob, direct_owner):
    direct_vm.mock_web(r"example\.com", {"status": 500, "body": "down"})
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)
    contract.resolve_claim(claim_id)

    contract.withdraw(claim_id)

    record = contract.get_claim(claim_id)
    assert record["withdrawn"] is True
    assert record["bond"] == 0
    assert contract.withdrawable(claim_id, as_hex_address(direct_owner)) == 0


def test_double_withdraw_reverts(direct_vm, direct_deploy, direct_bob):
    direct_vm.mock_web(r"example\.com", {"status": 500, "body": "down"})
    contract = deploy_claims(direct_deploy)
    claim_id = submit_claim(direct_vm, contract, direct_bob, value=10)
    contract.resolve_claim(claim_id)
    contract.withdraw(claim_id)

    with direct_vm.expect_revert("already withdrawn"):
        contract.withdraw(claim_id)


def test_resolve_unknown_claim_reverts(direct_vm, direct_deploy):
    contract = deploy_claims(direct_deploy)

    with direct_vm.expect_revert("unknown claim"):
        contract.resolve_claim("bcs-missing")


def test_withdraw_unknown_claim_reverts(direct_vm, direct_deploy):
    contract = deploy_claims(direct_deploy)

    with direct_vm.expect_revert("unknown claim"):
        contract.withdraw("bcs-missing")


def test_config_reports_value_parameters(direct_deploy):
    contract = deploy_claims(direct_deploy, min_bond=25, max_claims=7)

    config = contract.get_config()
    assert config["min_bond"] == 25
    assert config["max_claims"] == 7
    assert config["next_id"] == 1


def test_constructor_rejects_zero_min_bond(direct_vm, direct_deploy):
    with direct_vm.expect_revert("min_bond out of range"):
        deploy_claims(direct_deploy, min_bond=0)


def test_constructor_rejects_unbounded_claim_cap(direct_vm, direct_deploy):
    with direct_vm.expect_revert("max_claims out of range"):
        deploy_claims(direct_deploy, max_claims=10001)


def test_overlong_claim_reverts_before_truncation(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy, max_claim_chars=40)
    direct_vm.value = 10

    with direct_vm.expect_revert("claim is too long"):
        contract.submit_claim(
            "x" * 80,
            "https://example.com/evidence",
            as_hex_address(direct_bob),
            "consumer-a",
        )
    direct_vm.value = 0


def test_overlong_evidence_url_reverts_before_truncation(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy, max_url_chars=40)
    direct_vm.value = 10

    with direct_vm.expect_revert("evidence_url is too long"):
        contract.submit_claim(
            "Alice shipped milestone 4 according to the public status record.",
            "https://example.com/" + ("a" * 80),
            as_hex_address(direct_bob),
            "consumer-a",
        )
    direct_vm.value = 0


def test_latest_claim_for_unknown_consumer_is_blank(direct_deploy):
    contract = deploy_claims(direct_deploy)

    assert contract.latest_claim_for("nobody") == ""


def test_consumer_key_is_cleaned_before_indexing(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy)
    direct_vm.value = 10
    claim_id = contract.submit_claim(
        "Alice shipped milestone 4 according to the public status record.",
        "https://example.com/evidence",
        as_hex_address(direct_bob),
        " team\x00\n alpha ",
    )
    direct_vm.value = 0

    assert contract.latest_claim_for("team alpha") == claim_id


def test_sequential_claim_ids_are_monotonic(direct_vm, direct_deploy, direct_bob):
    contract = deploy_claims(direct_deploy)
    first = submit_claim(direct_vm, contract, direct_bob, value=10, consumer="a")
    second = submit_claim(direct_vm, contract, direct_bob, value=10, consumer="b")

    assert first == "bcs-1"
    assert second == "bcs-2"
