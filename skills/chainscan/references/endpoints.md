# Etherscan V2 endpoint inventory

Every URL is `https://api.etherscan.io/v2/api?` plus the params shown, with `&chainid=<CHAIN>&apikey={{vault:ETHERSCAN_API_KEY}}` always appended.

Free-tier columns: ✅ = available on free, 💰 = paid plan required (chains other than ETH/Polygon/Arbitrum). The `getabi`, `getsourcecode`, `verifysourcecode`, `checkverifystatus` endpoints are free on **all** chains.

## Accounts (`module=account`)

| Action | Free | Params | Description |
|---|---|---|---|
| `balance` | ✅/💰 | `address`, `tag=latest` | Native balance, returns wei string |
| `balancemulti` | ✅/💰 | `address` (comma-sep, ≤20), `tag=latest` | Bulk native balance |
| `txlist` | ✅/💰 | `address`, `startblock`, `endblock`, `page`, `offset`, `sort` | Normal transactions |
| `txlistinternal` | ✅/💰 | `address` or `txhash` or block range | Internal transactions |
| `tokentx` | ✅/💰 | `address`, `contractaddress?` | ERC-20 transfers |
| `tokennfttx` | ✅/💰 | `address`, `contractaddress?` | ERC-721 transfers |
| `token1155tx` | ✅/💰 | `address`, `contractaddress?` | ERC-1155 transfers |
| `tokenbalance` | ✅/💰 | `contractaddress`, `address`, `tag=latest` | ERC-20 balance, raw integer |
| `getminedblocks` | ✅/💰 | `address`, `blocktype` | Blocks mined by a validator |
| `txsBeaconWithdrawal` | ✅ | `address` | Beacon chain withdrawals (ETH only) |
| `balancehistory` | 💰 PRO | `address`, `blockno` | Historical native balance |

## Contracts (`module=contract`)

| Action | Free | Params | Description |
|---|---|---|---|
| `getabi` | ✅ | `address` | Contract ABI (JSON-stringified) |
| `getsourcecode` | ✅ | `address` | Source + ABI + metadata |
| `getcontractcreation` | ✅/💰 | `contractaddresses` (comma-sep, ≤5) | Creator + creation tx |
| `verifysourcecode` (POST) | ✅ | full source + compiler args | Submit verification |
| `checkverifystatus` | ✅ | `guid` | Poll verification status |
| `verifyproxycontract` (POST) | ✅ | `address`, `expectedimplementation?` | Verify a proxy |
| `checkproxyverification` | ✅ | `guid` | Poll proxy verification |

## Transactions (`module=transaction`)

| Action | Free | Params | Description |
|---|---|---|---|
| `getstatus` | ✅/💰 | `txhash` | Contract execution status (success/error) |
| `gettxreceiptstatus` | ✅/💰 | `txhash` | Tx receipt status (1=success, 0=fail) |

## Blocks (`module=block`)

| Action | Free | Params | Description |
|---|---|---|---|
| `getblockreward` | ✅/💰 | `blockno` | Block + uncle rewards |
| `getblockcountdown` | ✅/💰 | `blockno` | Estimated time to a future block |
| `getblocknobytime` | ✅/💰 | `timestamp`, `closest=before\|after` | Block at a unix timestamp |
| `dailyavgblocksize` | 💰 PRO | date range | Daily avg block size |
| `dailyblkcount` | 💰 PRO | date range | Daily block count |

## Logs (`module=logs`)

| Action | Free | Params | Description |
|---|---|---|---|
| `getLogs` | ✅/💰 | `address`, `fromBlock`, `toBlock`, `topic0..3`, `topic{i}_{j}_opr=and\|or`, `page`, `offset` | Event logs |

## Geth/Parity proxy (`module=proxy`)

Returns raw JSON-RPC shape `{jsonrpc, id, result}`. All proxy endpoints free on free-tier chains.

| Action | Params | Description |
|---|---|---|
| `eth_blockNumber` | — | Latest block number (hex) |
| `eth_getBlockByNumber` | `tag`, `boolean` | Block by number |
| `eth_getBlockTransactionCountByNumber` | `tag` | Tx count in a block |
| `eth_getTransactionByHash` | `txhash` | Tx by hash |
| `eth_getTransactionByBlockNumberAndIndex` | `tag`, `index` | Tx by block + index |
| `eth_getTransactionCount` | `address`, `tag` | Account nonce |
| `eth_sendRawTransaction` | `hex` | Broadcast signed tx |
| `eth_getTransactionReceipt` | `txhash` | Receipt + logs |
| `eth_call` | `to`, `data`, `tag` | Read-only contract call |
| `eth_getCode` | `address`, `tag` | Bytecode at address |
| `eth_getStorageAt` | `address`, `position`, `tag` | Storage slot value |
| `eth_gasPrice` | — | Current gas price |
| `eth_estimateGas` | tx params | Gas estimate |

## Tokens (`module=token`, `module=stats`)

| Module/Action | Free | Params | Description |
|---|---|---|---|
| `stats/tokensupply` | ✅/💰 | `contractaddress` | ERC-20 total supply |
| `stats/tokensupplyhistory` | 💰 PRO | `contractaddress`, `blockno` | Historical supply |
| `token/tokenholderlist` | 💰 PRO | `contractaddress`, `page`, `offset` | Top holders |
| `token/tokenholdercount` | 💰 PRO | `contractaddress` | Holder count |
| `token/tokeninfo` | 💰 PRO | `contractaddress` | Project info, social links, etc. |

## Gas (`module=gastracker`)

| Action | Free | Params | Description |
|---|---|---|---|
| `gasoracle` | ✅/💰 | — | Safe/Propose/Fast gas in gwei |
| `gasestimate` | ✅/💰 | `gasprice` | Confirmation time estimate |
| `dailyavggaslimit` | 💰 PRO | date range | Daily avg gas limit |
| `dailyavggasprice` | 💰 PRO | date range | Daily avg gas price |
| `dailygasused` | 💰 PRO | date range | Daily total gas used |

## Stats (`module=stats`)

| Action | Free | Description |
|---|---|---|
| `ethsupply` | ✅ (ETH only) | Total ETH supply |
| `ethsupply2` | ✅ (ETH only) | Supply incl. EIP-1559 + beacon |
| `ethprice` | ✅/💰 | Current native price (USD/BTC) |
| `bnbprice` | 💰 (BSC) | Current BNB price |
| `maticprice` | 💰 (Polygon) | Current MATIC price |
| `nodecount` | ✅/💰 | Active sync nodes (ETH only) |
| `dailynetutilization` | 💰 PRO | Daily network utilization |
| `dailytx` | 💰 PRO | Daily tx count |
| `chainsize` | 💰 PRO | Chain data size over time |

## Common response shapes

### Standard (most modules)

```json
{
  "status": "1",
  "message": "OK",
  "result": <varies>
}
```

Always check `status === "1"` (string). On failure: `status === "0"`, `message === "NOTOK"`, and `result` contains an error string like `"Max calls per sec rate limit reached, please try again later"` or `"Invalid API Key"`.

### Proxy module (raw JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": <raw rpc result, can be hex/object/null>
}
```

No `status` field. On error: `{"jsonrpc":"2.0","id":1,"error":{...}}`.

### Multi-result (logs, txlist, etc.)

`result` is an array. Empty arrays mean "no records," not an error — `status` is still `"1"`.

## Pagination defaults

- `txlist`, `tokentx`, `getLogs`: default `page=1`, `offset=10000` (drops to `1000` 2026-07-01).
- `getcontractcreation`: max **5 addresses** per call.
- `balancemulti`: max **20 addresses** per call.

## Rate-limiting behavior

When you hit the per-second cap:
- HTTP status: `200`
- Body: `{"status":"0","message":"NOTOK","result":"Max calls per sec rate limit reached, please try again later"}`

When the daily cap is exhausted: `result` says `"You have exceeded the daily request limit"`.

## Useful one-liners

```bash
# Pretty-print ABI
curl -s "...&module=contract&action=getabi&address=0x..." | python3 -c 'import sys,json; print(json.dumps(json.loads(json.load(sys.stdin)["result"]), indent=2))'

# Get just the contract name
curl -s "...&module=contract&action=getsourcecode&address=0x..." | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"][0]["ContractName"])'

# Tx success/fail
curl -s "...&module=transaction&action=gettxreceiptstatus&txhash=0x..." | python3 -c 'import sys,json; print("OK" if json.load(sys.stdin)["result"]["status"]=="1" else "FAIL")'

# Decode hex balance to ether
curl -s "...&module=account&action=balance&address=0x..." | python3 -c 'import sys,json; print(int(json.load(sys.stdin)["result"])/1e18, "ETH")'
```

## Forge integration

`forge verify-contract` automatically uses the V2 endpoint when `--chain-id` is supplied. The single Etherscan API key works across all supported chains:

```bash
forge verify-contract <ADDR> <ContractName> \
  --chain-id <CHAIN> \
  --etherscan-api-key {{vault:ETHERSCAN_API_KEY}} \
  --watch
```

For complex constructor args, use `--constructor-args $(cast abi-encode 'constructor(...)' <args>)`.
