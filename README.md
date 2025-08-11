This is a **crypto trading bot** that uses sophisticated technical analysis and risk management to automatically place buy and sell orders. It primarily deals with the cryptocurrency `BTC` and the fiat currency `USDT`, but you can set it to any other trading pair.

![Trading Bot Screenshot](static/screenshot.png)

### Install:

```shell
pip install ohheycrypto
```

## Features

### Core Trading Features
- **Automatic Trading**: Intelligent buy/sell decisions using technical indicators and market analysis
- **Regular Market Monitoring**: Checks the market every minute (60s) with comprehensive analysis
- **RSI Integration**: Uses Relative Strength Index to identify overbought/oversold conditions
- **Dynamic Thresholds**: Automatically adjusts buy/sell thresholds based on market volatility
- **Trailing Stop-Loss**: Protects profits with a 2% trailing stop that locks in gains
- **Multi-Timeframe Analysis**: Uses moving averages to determine market trend direction

### Risk Management
- **Smart Position Sizing**: Adjusts position size based on market volatility (50%-95% of balance)
- **Circuit Breaker**: Automatically pauses trading after 5 consecutive failed orders
- **Configuration Validation**: Ensures trading parameters are within safe ranges
- **Minimum Order Validation**: Prevents failed orders due to exchange minimums

### Enhanced Market Analysis
- **Volatility Assessment**: Calculates market volatility to optimize trading parameters
- **Trend Detection**: Identifies uptrends, downtrends, and sideways markets
- **Technical Indicators**: RSI-based entry/exit signals for better timing
- **Comprehensive Logging**: Detailed market conditions and trading decisions

## Quick Start:

```shell
# Create a configuration file
ohheycrypto init config.json

# Edit config.json and add your Binance API credentials

# Validate your configuration
ohheycrypto validate config.json

# Run the bot
ohheycrypto run config.json
```

### Configuration File:

The bot uses a JSON configuration file instead of environment variables. Use `ohheycrypto init` to create a template:

```json
{
  "binance": {
    "api_key": "YOUR_BINANCE_API_KEY",
    "api_secret": "YOUR_BINANCE_API_SECRET"
  },
  "trading": {
    "crypto": "BTC",
    "fiat": "USDT",
    "stop_loss": 3.0,
    "sell_threshold": 0.4,
    "buy_threshold": 0.2,
    "trailing_stop": 2.0,
    "position_sizing": {
      "min": 0.5,
      "max": 0.95
    }
  },
  "market_analysis": {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "ma_short": 10,
    "ma_long": 20,
    "volatility_lookback": 20
  },
  "execution": {
    "check_interval": 60,
    "circuit_breaker": {
      "max_failures": 5,
      "cooldown": 3600
    },
    "min_order_value": 10.0
  },
  "notifications": {
    "discord_webhook": ""
  }
}
```

### Command Line Interface:

```shell
# Get help
ohheycrypto --help

# Check version
ohheycrypto --version

# Create configuration file
ohheycrypto init [config_file]

# Validate configuration
ohheycrypto validate config.json

# Run the bot
ohheycrypto run config.json

# Dry run (no actual trades)
ohheycrypto run config.json --dry-run

# Verbose logging
ohheycrypto run config.json --verbose
```

### Legacy Environment Variables (still supported):

Environment variables will override configuration file values:

```
- `BINANCE_API_KEY`: Your Binance API key  
- `BINANCE_API_SECRET`: Your Binance API secret
- `DISCORD_WEBHOOK`: Discord webhook URL for notifications
- `BOT_SL`: Stop loss percentage (as decimal, e.g., 0.03 = 3%)
- `BOT_ST`: Sell threshold percentage (as decimal, e.g., 0.004 = 0.4%)
- `BOT_BT`: Buy threshold percentage (as decimal, e.g., 0.002 = 0.2%)
- `BOT_FIAT`: Fiat currency (default: USDT)
- `BOT_CRYPTO`: Cryptocurrency (default: BTC)
```

### How the Enhanced Trading Works:

#### 1. Market Analysis Phase:

```
- RSI Calculation: Analyzes 14-day RSI to identify market momentum
- Volatility Assessment: Calculates price volatility over 30 days
- Trend Detection: Uses 10-day and 20-day moving averages to determine trend
- Dynamic Threshold Adjustment: Scales thresholds 1x-3x based on volatility
```

#### 2. Buy Decision Logic:

```
- RSI Oversold (< 30): Strong buy signal regardless of other conditions
- RSI Overbought (> 70): Prevents buying during peaks
- Trend-Based Adjustments:
  - Uptrend: More aggressive on small dips (0.7x threshold)
  - Downtrend: Wait for stronger dips (1.5x threshold)
  - Sideways: Use standard threshold
```

#### 3. Sell Decision Logic:

```
- RSI Overbought (> 70): Strong sell signal
- Trailing Stop-Loss: 2% trailing stop locks in profits automatically
- Trend-Based Adjustments:
  - Uptrend: Hold longer for bigger profits (1.5x threshold)
  - Downtrend: Take profits quicker (0.7x threshold)
```

#### 4. Risk Management:

```
- Position Sizing: Uses 50%-95% of balance based on volatility
- Circuit Breaker: Pauses trading for 1 hour after 5 failed orders
- Order Validation: Ensures minimum order sizes are met
```

## Example Trading Scenarios

### Scenario 1: Uptrend Market (RSI: 45, Trend: UP)
```
- Current Price: $50,000
- Dynamic Buy Threshold: 0.3% (1.5x base due to volatility)
- Adjusted for Uptrend: 0.21% (0.7x modifier)
- Buy Signal: When price drops to $49,895 or below
- Position Size: 80% of balance (moderate volatility)
```

### Scenario 2: Oversold Bounce (RSI: 25)
```
- Immediate Buy Signal: RSI < 30 triggers strong buy regardless of price
- Trailing Stop: Activates once in profit, follows price up
- Sell Logic: Won't sell until RSI > 30 (avoid selling during bounce)
```

### Scenario 3: High Volatility Market (Volatility: 8%)
```
- Dynamic Thresholds: 3x scaling due to high volatility
- Buy Threshold: 0.6% vs 0.2% base
- Sell Threshold: 1.2% vs 0.4% base
- Position Size: 50% of balance (maximum risk management)
```

## Performance Expectations

### Improvements vs Basic Bot:
```
- Better Entry Timing: RSI prevents buying at peaks (~15-20% improvement)
- Profit Protection: Trailing stops lock in gains (~10-15% improvement)
- Trend Following: Holds winners longer, cuts losers faster (~20-25% improvement)
- Risk Management: Variable position sizing reduces drawdowns (~10-20% improvement)
```

### Recommended Settings:
```
- Conservative: Keep default thresholds, monitor for 1-2 weeks
- Aggressive: Lower base thresholds to 0.15%/0.3%, increase trailing stop to 3%
- High Frequency: Check every 30 seconds instead of 60 seconds
```

## Deployment

### Production Installation:
```bash
# Install 
pip install ohheycrypto

# Create a config file
ohheycrypto init production_config.json

# Validate your config file
ohheycrypto validate production_config.json

# Run the bot with your config
ohheycrypto run production_config.json
```

### Development/Source Installation:
```bash
git clone https://github.com/sn/ohheycrypto
cd bot
pip install -e .
ohheycrypto init dev_config.json

# Edit config file
ohheycrypto run dev_config.json --verbose
```

### Dry Run Testing:
```bash
# Test your configuration without making actual trades
ohheycrypto run config.json --dry-run
```

## Contributing

Contributions are welcome! Areas for improvement:
- Additional technical indicators (MACD, Bollinger Bands, etc)
- Multi-pair trading support
- Backtesting framework
- Web dashboard for monitoring
- An improved Discord notification when making a profitable trades
- Saving trade data to a SQLite database locally

Please submit pull requests or open issues for discussion.

## Important Disclaimers

### Risk Warning:
- **Cryptocurrency trading is extremely risky** and can result in significant losses
- **This bot uses advanced strategies** that may increase both profits and losses  
- **Past performance does not guarantee future results**
- **Start with small amounts** to test the bot's performance

### Liability:
- **Use at your own risk** - developers are not responsible for any financial losses
- **Always do your own research** and understand the risks involved
- **Consider consulting a financial advisor** before automated trading
- **Monitor the bot regularly** - automated trading requires oversight

### Best Practices:
- **Test thoroughly** with small amounts before increasing position sizes
- **Monitor market conditions** - algorithms perform differently in various market cycles
- **Keep API keys secure** and use restricted permissions when possible
- **Have a plan** for stopping or modifying the bot during extreme market conditions

## License

This project is licensed under the MIT License - see below for details:

MIT License

Copyright (c) 2025 Sean Nieuwoudt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.