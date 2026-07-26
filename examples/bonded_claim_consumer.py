# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


@gl.contract_interface
class IBondedClaimSlashing:
    class View:
        def claim_status(self, claim_id: str) -> str: ...
        def withdrawable(self, claim_id: str, account: str) -> u256: ...

    class Write:
        def submit_claim(
            self, claim: str, evidence_url: str, beneficiary: str, consumer_key: str
        ) -> str: ...
        def resolve_claim(self, claim_id: str) -> None: ...


class BondedClaimConsumer(gl.Contract):
    slasher: Address
    beneficiary: Address
    consumer_key: str
    last_claim_id: str

    def __init__(self, slasher: str, beneficiary: str, consumer_key: str = "demo"):
        self.slasher = Address(slasher)
        self.beneficiary = Address(beneficiary)
        self.consumer_key = consumer_key
        self.last_claim_id = ""

    @gl.public.write
    def remember_claim(self, claim_id: str) -> None:
        self.last_claim_id = claim_id

    @gl.public.write
    def ask_resolution(self) -> None:
        if self.last_claim_id == "":
            raise gl.vm.UserError("no claim")
        IBondedClaimSlashing(self.slasher).emit().resolve_claim(self.last_claim_id)

    @gl.public.view
    def status(self) -> dict:
        if self.last_claim_id == "":
            return {"claim_id": "", "status": "NONE", "beneficiary_withdrawable": 0}
        slasher = IBondedClaimSlashing(self.slasher)
        return {
            "claim_id": self.last_claim_id,
            "status": slasher.view().claim_status(self.last_claim_id),
            "beneficiary_withdrawable": int(
                slasher.view().withdrawable(self.last_claim_id, self.beneficiary.as_hex)
            ),
        }
