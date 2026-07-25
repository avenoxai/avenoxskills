# Chain ID + RPC reference

Every chain supported by Etherscan V2's unified API, with a default public RPC for use with `cast`. Free-tier availability marked per chain — chains marked **(paid)** require a paid Etherscan plan for non-`getabi`/`getsourcecode` endpoints.

## Tier 1 — heavy use

| Chain | chainid | Free? | Default RPC |
|---|---|---|---|
| Ethereum | `1` | YES | `https://eth.llamarpc.com` |
| Polygon | `137` | YES | `https://polygon-rpc.com` |
| Arbitrum One | `42161` | YES | `https://arb1.arbitrum.io/rpc` |
| BSC | `56` | paid | `https://bsc-dataseed.binance.org` |
| Base | `8453` | paid | `https://mainnet.base.org` |
| Optimism | `10` | paid | `https://mainnet.optimism.io` |
| Avalanche C | `43114` | paid | `https://api.avax.network/ext/bc/C/rpc` |

## Testnets

| Chain | chainid | Free? | Default RPC |
|---|---|---|---|
| Sepolia | `11155111` | YES | `https://ethereum-sepolia-rpc.publicnode.com` |
| Holesky | `17000` | YES | `https://holesky.drpc.org` |
| Hoodi | `560048` | YES | `https://rpc.hoodi.ethpandaops.io` |
| Polygon Amoy | `80002` | YES | `https://rpc-amoy.polygon.technology` |
| Arbitrum Sepolia | `421614` | YES | `https://sepolia-rollup.arbitrum.io/rpc` |
| BSC Testnet | `97` | paid | `https://data-seed-prebsc-1-s1.binance.org:8545` |
| Base Sepolia | `84532` | paid | `https://sepolia.base.org` |
| OP Sepolia | `11155420` | paid | `https://sepolia.optimism.io` |
| Avalanche Fuji | `43113` | paid | `https://api.avax-test.network/ext/bc/C/rpc` |

## L2s & rollups

| Chain | chainid | Free? | Default RPC |
|---|---|---|---|
| Arbitrum Nova | `42170` | paid | `https://nova.arbitrum.io/rpc` |
| Linea | `59144` | paid | `https://rpc.linea.build` |
| Scroll | `534352` | paid | `https://rpc.scroll.io` |
| zkSync Era | `324` | paid | `https://mainnet.era.zksync.io` |
| Polygon zkEVM | `1101` | paid | `https://zkevm-rpc.com` |
| Mantle | `5000` | paid | `https://rpc.mantle.xyz` |
| Blast | `81457` | paid | `https://rpc.blast.io` |
| Fraxtal | `252` | paid | `https://rpc.frax.com` |
| Mode | `34443` | paid | `https://mainnet.mode.network` |
| Taiko | `167000` | paid | `https://rpc.mainnet.taiko.xyz` |
| Celo | `42220` | paid | `https://forno.celo.org` |
| Gnosis | `100` | paid | `https://rpc.gnosischain.com` |
| Moonbeam | `1284` | paid | `https://rpc.api.moonbeam.network` |
| Moonriver | `1285` | paid | `https://rpc.api.moonriver.moonbeam.network` |
| Cronos | `25` | paid | `https://evm.cronos.org` |
| Fantom | `250` | paid | `https://rpc.ftm.tools` |
| Sonic | `146` | paid | `https://rpc.soniclabs.com` |
| Berachain | `80094` | paid | `https://rpc.berachain.com` |
| Sei (EVM) | `1329` | paid | `https://evm-rpc.sei-apis.com` |
| Unichain | `130` | paid | `https://mainnet.unichain.org` |
| World Chain | `480` | paid | `https://worldchain-mainnet.g.alchemy.com/public` |
| Apechain | `33139` | paid | `https://apechain.calderachain.xyz/http` |
| ABstract | `2741` | paid | `https://api.mainnet.abs.xyz` |
| Sophon | `50104` | paid | `https://rpc.sophon.xyz` |

## Getting a public RPC

When the default RPC throttles or 5xxs:
- Llama Nodes: `https://*.llamarpc.com`
- Ankr public: `https://rpc.ankr.com/<chain>`
- dRPC public: `https://<chain>.drpc.org`
- Chain's official docs page lists more

## Verifying chain ID at runtime

```bash
cast chain-id --rpc-url <RPC>
```

Use this to sanity-check that the RPC you're hitting matches the chainid you passed to V2.
