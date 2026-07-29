import fs from "node:fs";
import { Wallet } from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/ethers/lib.esm/index.js";
import {
  chains,
  createAccount,
  createClient,
} from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist/index.js";

const secretsRaw = fs
  .readFileSync("../visual-state-gate/.deploy-secrets.json", "utf8")
  .replace(/^\uFEFF/, "");
const secrets = JSON.parse(secretsRaw);
const keystore = fs.readFileSync(
  `C:/Users/DELL/.genlayer/keystores/${secrets.account}.json`,
  "utf8",
);
const wallet = await Wallet.fromEncryptedJson(keystore, secrets.password);
const account = createAccount(wallet.privateKey);
const client = createClient({ chain: chains.studionet, account });

const code = fs.readFileSync("contracts/bonded_claim_slashing.py", "utf8");
const claimant = account.address;
const beneficiary = account.address;
const consumerKey = `bonded-resubmission-${Date.now()}`;
const claim =
  "The public Example Domain page identifies itself with the heading Example Domain.";
const evidenceUrl = "https://example.com";

async function wait(hash, label, retries = 90) {
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: "ACCEPTED",
    interval: 5000,
    retries,
  });
  console.log(label, JSON.stringify({
    hash,
    status: receipt.status_name,
    result: receipt.result_name,
    contractAddress: receipt.contract_address ?? receipt.contractAddress ?? null,
  }));
  return receipt;
}

async function write(address, functionName, args, value = 0n, retries = 90) {
  const hash = await client.writeContract({
    account,
    address,
    functionName,
    args,
    value,
    consensusMaxRotations: 3,
  });
  await wait(hash, functionName, retries);
  return hash;
}

console.log("account", claimant);
const deployHash = await client.deployContract({
  account,
  code,
  args: [1, 1000, 3, 700, 320, 500],
  consensusMaxRotations: 3,
});
const deployReceipt = await wait(deployHash, "deploy", 120);
const contract =
  deployReceipt.contract_address ??
  deployReceipt.contractAddress ??
  deployReceipt.data?.contract_address ??
  deployReceipt.data?.contractAddress;
if (!contract) {
  console.log("deploy receipt keys", Object.keys(deployReceipt));
  throw new Error("could not find deployed contract address in receipt");
}

const submitHash = await write(contract, "submit_claim", [
  claim,
  evidenceUrl,
  beneficiary,
  consumerKey,
], 1n);

const claimId = await client.readContract({
  address: contract,
  functionName: "latest_claim_for",
  args: [consumerKey],
});
console.log("claimId", claimId);
console.log("afterSubmit", JSON.stringify(await client.readContract({
  address: contract,
  functionName: "get_claim",
  args: [claimId],
}), null, 2));

const resolveHash = await write(contract, "resolve_claim", [claimId], 0n, 120);
const afterResolve = await client.readContract({
  address: contract,
  functionName: "get_claim",
  args: [claimId],
});
console.log("afterResolve", JSON.stringify(afterResolve, null, 2));

const claimantWithdrawable = await client.readContract({
  address: contract,
  functionName: "withdrawable",
  args: [claimId, claimant],
});
const beneficiaryWithdrawable = await client.readContract({
  address: contract,
  functionName: "withdrawable",
  args: [claimId, beneficiary],
});
console.log("withdrawableClaimant", claimantWithdrawable?.toString?.() ?? claimantWithdrawable);
console.log("withdrawableBeneficiary", beneficiaryWithdrawable?.toString?.() ?? beneficiaryWithdrawable);

let withdrawHash = "";
if ((claimantWithdrawable?.toString?.() ?? String(claimantWithdrawable)) !== "0") {
  withdrawHash = await write(contract, "withdraw", [claimId]);
}

const finalClaim = await client.readContract({
  address: contract,
  functionName: "get_claim",
  args: [claimId],
});
const config = await client.readContract({
  address: contract,
  functionName: "get_config",
  args: [],
});

console.log("summary", JSON.stringify({
  contract,
  deployHash,
  submitHash,
  resolveHash,
  withdrawHash,
  claimId,
  consumerKey,
  finalClaim,
  config,
}, null, 2));
