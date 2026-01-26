# Polymarket Arbitrage Bot

Production-ready Python trading bot for Polymarket with gasless transactions and real-time WebSocket orderbook streaming.

## Features

- **Gasless Trading** - Builder Program integration for zero gas fees
- **Real-time WebSocket** - Live orderbook updates and market data
- **15-Minute Markets** - Built-in support for BTC/ETH/SOL/XRP markets
- **Flash Crash Strategy** - Pre-built volatility trading strategy
- **Secure Storage** - PBKDF2 + Fernet encrypted private key storage
- **Simple API** - Clean, intuitive Python interface

## Quick Start

### Installation

```bash
git clone https://github.com/vladmeer/polymarket-arbitrage-bot.git
cd polymarket-arbitrage-bot
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
export POLY_PRIVATE_KEY=your_private_key
export POLY_PROXY_WALLET=0xYourPolymarketProxyWallet
```

> **PROXY WALLET**: Find at [polymarket.com/settings](https://polymarket.com/settings)

### Quick Start - Orderbook Viewer

View real-time orderbook data (read-only, no trading):

```bash
# View ETH market orderbook
python apps/orderbook_viewer.py --coin ETH

```
<img width="690" height="476" alt="image (1)" src="https://github.com/user-attachments/assets/83621505-41e7-4b5a-90fd-3c84d1610291" />

**Note:** Orderbook viewer doesn't require credentials - it's a read-only monitoring tool.

### Quick Start - Flash Crash Strategy

Run the automated trading strategy:

```bash
# Run with default settings (ETH, $5 size, 30% drop threshold)
python apps/flash_crash_runner.py --coin ETH

```
<img width="693" height="401" alt="image (2)" src="https://github.com/user-attachments/assets/d5ccffc8-20c5-4cd1-9c3b-679099b22899" />

**Note:** Flash crash strategy requires `POLY_PRIVATE_KEY` and `POLY_PROXY_WALLET` environment variables.

## Trading Strategies

### Flash Crash Strategy

Monitors 15-minute markets for sudden probability drops and executes trades automatically.

```bash
# Default settings
python apps/flash_crash_runner.py --coin BTC

```

**Parameters:**
- `--coin` - BTC, ETH, SOL, XRP (default: ETH)
- `--drop` - Drop threshold (default: 0.30)
- `--size` - Trade size in USDC (default: 5.0)
- `--lookback` - Detection window in seconds (default: 10)
- `--take-profit` - Take profit in dollars (default: 0.10)
- `--stop-loss` - Stop loss in dollars (default: 0.05)

### Orderbook Viewer

Real-time orderbook visualization:

```bash
python apps/orderbook_viewer.py --coin BTC
```

## Usage Examples

### Basic Usage

```python
from src import create_bot_from_env
import asyncio

async def main():
    bot = create_bot_from_env()
    orders = await bot.get_open_orders()
    print(f"Open orders: {len(orders)}")

asyncio.run(main())
```

### Place Order

```python
from src import TradingBot, Config

bot = TradingBot(config=Config(safe_address="0x..."), private_key="0x...")
result = await bot.place_order(token_id="...", price=0.65, size=10.0, side="BUY")
```

### WebSocket Streaming

```python
from src.websocket_client import MarketWebSocket

ws = MarketWebSocket()
ws.on_book = lambda s: print(f"Price: {s.mid_price:.4f}")
await ws.subscribe(["token_id"])
await ws.run()
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POLY_PRIVATE_KEY` | Yes | Wallet private key |
| `POLY_PROXY_WALLET` | Yes | Polymarket Proxy wallet address |
| `POLY_BUILDER_API_KEY` | Optional | Builder Program API key (gasless) |
| `POLY_BUILDER_API_SECRET` | Optional | Builder Program API secret |
| `POLY_BUILDER_API_PASSPHRASE` | Optional | Builder Program passphrase |

## Gasless Trading

Enable gasless trading via Builder Program:

1. Apply at [polymarket.com/settings?tab=builder](https://polymarket.com/settings?tab=builder)
2. Set environment variables: `POLY_BUILDER_API_KEY`, `POLY_BUILDER_API_SECRET`, `POLY_BUILDER_API_PASSPHRASE`

The bot automatically uses gasless mode when credentials are present.

## Security

Private keys are encrypted using PBKDF2 (480,000 iterations) + Fernet symmetric encryption. Best practices:

- Never commit `.env` files
- Use a dedicated trading wallet
- Keep encrypted key files secure (permissions: 0600)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Trading tool

I've also developed a trading bot for Polymarket built with **Rust**.

<img width="1917" height="942" alt="image (21)" src="https://github.com/user-attachments/assets/08a5c962-7f8b-4097-98b6-7a457daa37c9" />
https://www.youtube.com/watch?v=4f6jHT4-DQs

## Recommend VPS

Vps: [@TradingVps](https://app.tradingvps.io/aff.php?aff=57)
<img width="890" height="595" alt="534038982-fb311b59-05a6-477a-a8f0-5e8291acf1eb" src="https://github.com/user-attachments/assets/72966dac-3faa-4e93-941e-a34026d59822" />

## Version 2 - Dutch Book Arbitrage Tool

I built **Polymarket Dutch Book Arbitrage Bot** - An automated trading system that detects guaranteed-profit opportunities in Polymarket's binary markets. When UP + DOWN token prices sum to less than 1.0, the bot simultaneously buys both, locking in a risk-free profit. Real-time WebSocket monitoring with 5-40ms detection latency.
<img width="932" height="389" alt="image (3)" src="https://github.com/user-attachments/assets/c2858820-d61c-4568-8e9f-6784ffbcc7df" />
<img width="1280" height="689" alt="image (4)" src="https://github.com/user-attachments/assets/79d2b280-be8d-40bf-9af5-7b969b6ae353" />
<img width="1149" height="312" alt="image (5)" src="https://github.com/user-attachments/assets/fe067f71-0e5d-47d3-a9cd-f136757cb91d" />


If you need this tool, contact me.

**Disclaimer:** This software is for educational purposes only. Trading involves risk of loss. The developers are not responsible for any financial losses incurred while using this bot.

**Support:** For questions or issues, contact via Telegram: [@Vladmeer](https://t.me/vladmeer67) | Twitter: [@Vladmeer](https://x.com/vladmeer67)
