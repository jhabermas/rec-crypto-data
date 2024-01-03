# rec-crypto-data

Scripts for continuously recording market data from crypto exchanges and APIs. The data is fetched asynchronously using ccxt, cryptofeed and via REST APIs. The endpoints, channels and symbols are configurable. Data is saved to provided sink. See `config/settings.toml` for details.

## Usage for Development

```bash
pip install -e .
cd rcd && python rec_data.py
```
