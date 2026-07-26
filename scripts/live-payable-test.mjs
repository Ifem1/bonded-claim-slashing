import fs from "node:fs";
import { Wallet } from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/ethers/lib.esm/index.js";
import {
  chains,
  createAccount,
  createClient,
} from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist/index.js";

const contract = process.argv[2];
if (!contract) {
  throw new Error("usage: node scripts/live-payable-test.mjs <contract-address>");
}

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

const claimant = account.address;
const beneficiary = account.address;
const claim =
  "The public Example Domain page identifies itself with the heading Example Domain.";
const evidenceUrl = "https://example.com";
const consumerKey = "bonded-live-demo";

console.log(JSON.stringify({ account: claimant, contract }, null, 2));

const submitHash = await client.writeContract({
  account,
  address: contract,
  functionName: "submit_claim",
  args: [claim, evidenceUrl, beneficiary, consumerKey],
  value: 1n,
  consensusMaxRotations: 3,
});
console.log("submit_claim tx", submitHash);
const submitReceipt = await client.waitForTransactionReceipt({
  hash: submitHash,
  status: "ACCEPTED",
  interval: 5000,
  retries: 90,
});
console.log("submit_claim status", submitReceipt.status_name, submitReceipt.result_name);

const latest = await client.readContract({
  address: contract,
  functionName: "latest_claim_for",
  args: [consumerKey],
});
console.log("latest claim", latest);

const afterSubmit = await client.readContract({
  address: contract,
  functionName: "get_claim",
  args: [latest],
});
console.log("after submit", JSON.stringify(afterSubmit, null, 2));

const resolveHash = await client.writeContract({
  account,
  address: contract,
  functionName: "resolve_claim",
  args: [latest],
  value: 0n,
  consensusMaxRotations: 3,
});
console.log("resolve_claim tx", resolveHash);
const resolveReceipt = await client.waitForTransactionReceipt({
  hash: resolveHash,
  status: "ACCEPTED",
  interval: 5000,
  retries: 90,
});
console.log("resolve_claim status", resolveReceipt.status_name, resolveReceipt.result_name);

const afterResolve = await client.readContract({
  address: contract,
  functionName: "get_claim",
  args: [latest],
});
console.log("after resolve", JSON.stringify(afterResolve, null, 2));

const withdrawable = await client.readContract({
  address: contract,
  functionName: "withdrawable",
  args: [latest, claimant],
});
console.log("withdrawable claimant", withdrawable?.toString?.() ?? withdrawable);

if ((withdrawable?.toString?.() ?? String(withdrawable)) !== "0") {
  const withdrawHash = await client.writeContract({
    account,
    address: contract,
    functionName: "withdraw",
    args: [latest],
    value: 0n,
    consensusMaxRotations: 3,
  });
  console.log("withdraw tx", withdrawHash);
  const withdrawReceipt = await client.waitForTransactionReceipt({
    hash: withdrawHash,
    status: "ACCEPTED",
    interval: 5000,
    retries: 90,
  });
  console.log("withdraw status", withdrawReceipt.status_name, withdrawReceipt.result_name);

  const afterWithdraw = await client.readContract({
    address: contract,
    functionName: "get_claim",
    args: [latest],
  });
  console.log("after withdraw", JSON.stringify(afterWithdraw, null, 2));
}
