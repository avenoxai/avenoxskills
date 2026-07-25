---
name: chainscan
description: "Multi-chain block explorer queries via Etherscan V2 unified API + Foundry cast fallbacks. Look up contract ABI/source, transactions, receipts, event logs, balances, token info, contract creation, gas prices, verify contracts across Ethereum, BSC, Polygon, Arbitrum, Optimism, Base, Avalanche, Sepolia and 60+ other chains. One API key, one endpoint, any chain. Triggers on: etherscan, bscscan, polygonscan, arbiscan, basescan, optimism explorer, snowtrace, scan API, block explorer, contract lookup, get ABI, get source code, verify contract, tx lookup, receipt lookup, event logs, contract creation, contract creator, token holders, gas oracle, abi fetch."
---

# Chainscan — Etherscan V2 unified explorer skill

Query any major EVM chain's block explorer via the Etherscan V2 unified API, with Foundry `cast` as a fallback for paid-tier endpoints. **One Etherscan.io API key works across every supported chain** through V2 — BscScan/PolygonScan/etc. keys do **not** work and are no longer needed.

> Etherscan V1 was deprecated **2025-08-15**. V2 is the only API path going forward.

## Configuration

```
Base URL:        https://api.etherscan.io/v2/api
API key:         {{vault:ETHERSCAN_API_KEY}}
Auth pattern:    &apikey={{vault:ETHERSCAN_API_KEY}}
Chain selector:  &chainid=<id>   (REQUIRED on every call — no default)
Free tier:       3 req/sec, 100k req/day
```

## Chain ID quick reference

Most-used chains:

| Chain | chainid | Native | Default RPC |
|---|---|---|---|
| Ethereum mainnet | `1` | ETH | `https://eth.llamarpc.com` |
| BSC | `56` | BNB | `https://bsc-dataseed.binance.org` |
| Polygon | `137` | MATIC | `https://polygon-rpc.com` |
| Arbitrum One | `42161` | ETH | `https://arb1.arbitrum.io/rpc` |
| Optimism | `10` | ETH | `https://mainnet.optimism.io` |
| Base | `8453` | ETH | `https://mainnet.base.org` |
| Avalanche C-chain | `43114` | AVAX | `https://api.avax.network/ext/bc/C/rpc` |
| Sepolia | `11155111` | ETH | `https://ethereum-sepolia-rpc.publicnode.com` |
| Base Sepolia | `84532` | ETH | `https://sepolia.base.org` |
| Arbitrum Sepolia | `421614` | ETH | `https://sepolia-rollup.arbitrum.io/rpc` |

Full list: see `references/chains.md`.

## Free-tier endpoint availability

This is the most important table to internalize. Many endpoints are gated behind paid plans on non-Ethereum chains.

| Endpoint | ETH (1) | Polygon (137) | Arbitrum (42161) | BSC (56) | Base (8453) | OP (10) | Avalanche (43114) |
|---|---|---|---|---|---|---|---|
| `getabi` | YES | YES | YES | **YES** | **YES** | **YES** | **YES** |
| `getsourcecode` | YES | YES | YES | **YES** | **YES** | **YES** | **YES** |
| `verifysourcecode` | YES | YES | YES | **YES** | **YES** | **YES** | **YES** |
| `checkverifystatus` | YES | YES | YES | **YES** | **YES** | **YES** | **YES** |
| `getcontractcreation` | YES | YES | YES | NO | NO | NO | NO |
| `balance`, `txlist`, `tokentx`, `getLogs`, gas, prices | YES | YES | YES | NO | NO | NO | NO |

**Bolded YES** = available on all plans including free for that chain. So contract ABI/source and verification work everywhere; everything else needs `cast` on paid chains.

## Etherscan V2 endpoints

Every URL adds `&chainid=<CHAIN>&apikey={{vault:ETHERSCAN_API_KEY}}`. Replace `<CHAIN>` with the chain ID from the table above.

### Contract ABI

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=contract&action=getabi&address=<ADDR>&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

Returns `result` as a JSON-stringified ABI array. Pipe through `python3 -c 'import sys,json; print(json.dumps(json.loads(json.load(sys.stdin)["result"]), indent=2))'` to fully decode.

### Verified source code

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=contract&action=getsourcecode&address=<ADDR>&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

Returns: `SourceCode`, `ABI`, `ContractName`, `CompilerVersion`, `OptimizationUsed`, `Runs`, `ConstructorArguments`, `LicenseType`, `Proxy`, `Implementation`. For proxies, the returned ABI is the proxy's; fetch `Implementation` separately for the impl ABI.

### Contract creation tx (creator + creation hash)

Free on Ethereum/Polygon/Arbitrum, paid elsewhere. **Max 5 addresses per call** (comma-separated).

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=contract&action=getcontractcreation&contractaddresses=<ADDR1>,<ADDR2>&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

For paid chains, fall back to a binary-search using `cast code`. See "Find deployment block" below.

### Transaction by hash

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=proxy&action=eth_getTransactionByHash&txhash=<TXHASH>&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

> The `proxy` module returns raw JSON-RPC shape `{jsonrpc, id, result}`, **not** the standard `{status, message, result}` wrapper. Handle both shapes when parsing.

### Transaction receipt (logs, status)

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=proxy&action=eth_getTransactionReceipt&txhash=<TXHASH>&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

### Event logs

Free on Ethereum/Polygon/Arbitrum, paid elsewhere.

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=logs&action=getLogs&address=<ADDR>&fromBlock=<FROM>&toBlock=<TO>&topic0=<HASH>&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

Pagination: `&page=1&offset=1000`. Multiple topics: `topic1`, `topic2`, `topic3`, with `topic0_1_opr=and|or` for combinators.

> Effective **2026-07-01**, free-tier `getLogs` and `txlist` max records drop from 10,000 to 1,000 per request. Paginate.

### Native balance

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=account&action=balance&address=<ADDR>&tag=latest&apikey={{vault:ETHERSCAN_API_KEY}}"
```

Returns wei as a string. Multi-address: `action=balancemulti&address=<ADDR1>,<ADDR2>` (max 20).

### ERC-20 token balance

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=account&action=tokenbalance&contractaddress=<TOKEN>&address=<HOLDER>&tag=latest&apikey={{vault:ETHERSCAN_API_KEY}}"
```

Returns raw integer (no decimals applied). Fetch `decimals()` separately to format.

### Normal txs for an address

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=account&action=txlist&address=<ADDR>&startblock=0&endblock=99999999&page=1&offset=100&sort=desc&apikey={{vault:ETHERSCAN_API_KEY}}" | python3 -m json.tool
```

Use `action=tokentx` for ERC-20 transfers, `action=tokennfttx` for NFTs.

### Verify contract source (POST)

```bash
curl -s -X POST "https://api.etherscan.io/v2/api" \
  -d "chainid=<CHAIN>" \
  -d "module=contract" \
  -d "action=verifysourcecode" \
  -d "apikey={{vault:ETHERSCAN_API_KEY}}" \
  -d "contractaddress=<ADDR>" \
  -d "sourceCode=<STANDARD_JSON_INPUT>" \
  -d "codeformat=solidity-standard-json-input" \
  -d "contractname=<File.sol>:<ContractName>" \
  -d "compilerversion=v0.8.26+commit.8a97fa7a" \
  -d "optimizationUsed=1" \
  -d "runs=200" \
  -d "constructorArguements=<ABI_ENCODED_ARGS>" \
  -d "licenseType=3"
```

License IDs: 1=No License, 2=Unlicense, **3=MIT**, 4=GPL-2.0, 5=GPL-3.0, 6=LGPL-2.1, 7=LGPL-3.0, 8=BSD-2-Clause, 9=BSD-3-Clause, 10=MPL-2.0, 11=OSL-3.0, **12=Apache-2.0**, 13=AGPL-3.0, 14=BUSL-1.1.

### Check verification status

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<CHAIN>&module=contract&action=checkverifystatus&guid=<GUID>&apikey={{vault:ETHERSCAN_API_KEY}}"
```

### Verify with Forge (preferred)

```bash
forge verify-contract <ADDR> <ContractName> \
  --chain-id <CHAIN> \
  --etherscan-api-key {{vault:ETHERSCAN_API_KEY}} \
  --watch
```

Forge handles the V2 endpoint URL automatically.

## Foundry `cast` fallbacks (for paid endpoints)

Use these when the chain isn't on the free tier (BSC, Base, OP, Avalanche, etc.). Pass `--rpc-url <RPC>` from the chain table.

```bash
# Native balance
cast balance <ADDR> --rpc-url <RPC> --ether

# Contract code (existence check)
cast code <ADDR> --rpc-url <RPC> | head -c 80     # "0x" if no contract

# Tx + receipt
cast tx <TXHASH> --rpc-url <RPC>
cast receipt <TXHASH> --rpc-url <RPC>

# Block / chain state
cast block-number --rpc-url <RPC>
cast block <BLOCK> --rpc-url <RPC>
cast gas-price --rpc-url <RPC>
cast nonce <ADDR> --rpc-url <RPC>

# Storage slot
cast storage <ADDR> <SLOT> --rpc-url <RPC>

# Read calls
cast call <ADDR> "name()(string)" --rpc-url <RPC>
cast call <ADDR> "balanceOf(address)(uint256)" <HOLDER> --rpc-url <RPC>

# Event logs (raw)
cast logs --from-block <FROM> --to-block <TO> \
  --address <ADDR> "Transfer(address,address,uint256)" \
  --rpc-url <RPC>

# By topic hash
cast logs --from-block <FROM> --to-block <TO> \
  --address <ADDR> --topic0 <HASH> --rpc-url <RPC>

# Decoders / encoders
cast 4byte-decode 0x<METHOD_ID>          # selector → signature
cast calldata-decode "fn(types)" 0x<DATA>
cast sig "transfer(address,uint256)"     # signature → selector
cast keccak "Transfer(address,address,uint256)"  # event topic

# Unit conversions
cast to-wei 1.5 ether
cast from-wei <WEI>
cast to-hex <DEC>
cast to-dec 0x<HEX>
```

### Find contract deployment block (binary search)

When `getcontractcreation` is paid on the chain, binary-search with `cast code`:

```bash
# Returns "0x" if not deployed at <BLOCK>, else has bytecode
cast code <ADDR> --block <BLOCK> --rpc-url <RPC> | head -c 10
```

Algorithm: midpoint check, halve range based on whether code exists, until you converge to the exact deployment block. ~25 calls for any block range up to current head.

## Critical gotchas

1. **`status === "1"` (string)** — V2 returns success as `"1"` not `1` and not `true`. Bad calls return HTTP 200 with `{"status":"0","message":"NOTOK","result":"..."}`. Always check `status === "1"`, never truthy `result`.
2. **`chainid` is required.** Missing it returns an error, not a default-to-Ethereum.
3. **Old chain-specific keys (BscScan, PolygonScan) don't work on V2.** Must be an Etherscan.io key.
4. **`proxy` module returns raw JSON-RPC shape** `{jsonrpc, id, result}`, not the standard wrapper. Other modules return `{status, message, result}`.
5. **`getsourcecode` proxies**: check the `Proxy` (`"1"`/`"0"`) and `Implementation` fields. For proxies the returned ABI is the proxy's, not the impl's.
6. **`getcontractcreation` caps at 5 addresses per call.** Batch larger lookups.
7. **`tokenbalance` returns raw integer.** Always fetch `decimals()` to format.
8. **Rate limits**: 3 req/sec, 100k/day on free. Space rapid-fire calls or you'll start getting `Max calls per sec rate limit reached` strings in `result`.
9. **`getLogs`/`txlist` 10k → 1k pagination cap effective 2026-07-01.** Paginate now, future-self thanks you.
10. **Native-currency price endpoints (`bnbprice`, `ethprice`, etc.) are paid on most chains.** Use CoinGecko (`api.coingecko.com/api/v3/simple/price`) for free.

## Decision flow

When the user asks for chain data:

1. **Need ABI or source?** → Etherscan V2 (free on every chain).
2. **Need a tx, receipt, balance, log, or read call?** → if chain ∈ {ETH, Polygon, Arbitrum}, use V2; else use `cast` with the RPC.
3. **Verifying a contract?** → `forge verify-contract` is the easiest path, V2 POST is the manual fallback.
4. **Paid endpoint on a paid chain?** → use `cast` (free, fast, no rate limit beyond RPC).
5. **Native price?** → CoinGecko, not the explorer.

## References

- `references/chains.md` — complete chain ID + RPC inventory (60+ chains).
- `references/endpoints.md` — every V2 endpoint with full parameter list.

## Notes

- The same Etherscan.io key in this skill is also referenced by `~/.claude/skills/bscscan/SKILL.md`. They share the key intentionally — V2 unified everything, so one key serves both skills. The `bscscan` skill is BSC-specific; this `chainscan` skill is the general multi-chain version.

