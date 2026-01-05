# Polymarket Signal Detector

Real-time trading signal detection system for Polymarket markets.

## Features

- **Real-time Trade Monitoring**: WebSocket connection to Polymarket CLOB for live trade data
- **Signal Detection**: Multiple signal types including fresh wallets, size anomalies, timing analysis, and more
- **Discord Alerts**: Rate-limited alerts sent to Discord webhook
- **API Integration**: Comprehensive Polymarket API client with caching
- **Database Storage**: Track trades, signals, and trader statistics

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd polymarket
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord webhook URL
   ```

4. **Edit configuration** (optional)
   ```bash
   # Edit config.yaml to customize thresholds and settings
   vim config.yaml
   ```

## Usage

### Basic Usage

Run the signal detector:

```bash
python main.py
```

The system will:
1. Connect to Polymarket WebSocket
2. Monitor live trades
3. Detect trading signals
4. Send alerts to Discord

### Configuration

Edit `config.yaml` to customize:

- **Filters**: Excluded markets, timeframes, minimum trade size
- **Signal Detection**: Thresholds for each signal type
- **Discord**: Webhook URL, rate limits
- **Database**: SQLite or PostgreSQL
- **Logging**: Log level, file location

### Environment Variables

Set in `.env` file:

- `DISCORD_WEBHOOK_URL`: Your Discord webhook URL (required)
- `DATABASE_URL`: PostgreSQL connection string (optional, defaults to SQLite)

## Architecture

```
polymarket-signal-detector/
├── config.yaml              # Configuration
├── main.py                  # Entry point
├── src/
│   ├── websocket/          # WebSocket listener
│   ├── filters/            # Trade filters
│   ├── signals/            # Signal detectors
│   ├── enrichment/         # Profile & stats fetching
│   ├── discord/            # Discord integration
│   ├── api/                # Polymarket API client
│   ├── database/           # Database models
│   └── utils/              # Utilities
└── database/               # SQLite database
```

## API Endpoints Used

### Polymarket APIs

- **WebSocket**: `wss://ws-subscriptions-clob.polymarket.com/ws/market`
- **Data API**: `https://data-api.polymarket.com`
  - `/trades` - Historical trades
  - `/positions` - User positions
  - `/closed-positions` - Closed positions
  - `/traded` - Markets traded count
- **Gamma API**: `https://gamma-api.polymarket.com`
  - `/public-profile` - User profiles
  - `/markets` - Market metadata
- **CLOB API**: `https://clob.polymarket.com`
  - `/midpoint` - Market odds
  - `/price` - Buy/sell prices

## Signal Types

The system detects the following trading signals:

1. **Fresh Wallet**: New traders (< 30 days old)
2. **Size Anomaly**: Trades significantly larger than user's average
3. **Timing**: Trades shortly after market creation
4. **Odds Movement**: Trades during significant price movements
5. **Contrarian**: Trades against strong consensus
6. **Cluster**: Multiple similar wallets trading together

## Development Status

### Phase 1: Foundation ✅ (COMPLETED)
- [x] Project structure
- [x] Configuration files
- [x] API client wrapper
- [x] WebSocket listener
- [x] Database models
- [x] Logging setup
- [x] Main entry point

### Phase 2: Filtering (In Progress)
- [ ] Market filter (categories, timeframes)
- [ ] Size filter
- [ ] LP detection logic

### Phase 3: Signal Detection (Planned)
- [ ] Fresh wallet detector
- [ ] Size anomaly detector
- [ ] Timing analyzer
- [ ] Odds movement tracker
- [ ] Contrarian detector
- [ ] Cluster detector

### Phase 4: Enrichment & Alerts (Planned)
- [ ] Profile fetcher
- [ ] Win rate calculator
- [ ] Discord queue system
- [ ] Alert formatting

## Testing

Run tests:

```bash
pytest tests/
```

## Monitoring

The system prints statistics every 60 seconds (configurable) including:

- Trades processed
- Signals detected
- Alerts sent
- Cache hit rate
- WebSocket status

## Database

By default, uses SQLite at `database/signals.db`.

For PostgreSQL, set in `config.yaml`:
```yaml
database:
  type: postgresql
  postgres_url: "postgresql://user:pass@localhost:5432/polymarket"
```

## Contributing

1. Create a feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

MIT License

## Support

For issues and questions, please open a GitHub issue.

---

**Built with:** Python 3.9+, WebSockets, SQLAlchemy, Polymarket APIs
