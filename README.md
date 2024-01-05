# rec-crypto-data

Scripts for continuously recording market data from crypto exchanges and APIs. The data is fetched asynchronously using ccxt, cryptofeed and via REST APIs. The endpoints, channels and symbols are configurable. Data is saved to provided sink (e.g. file / database). See `rcd/sinks`.

## Configuration

To override default configuration create a `settings.local.toml` in the `config` folder. This will be automatically loaded and override default configuration.

For managing keys and credentials create `.secrets.toml` file.

The settings can also be set using environment variables prefixed with `RCD_`, e.g. `export RCD_FETCH_OB=0` and `export RCD_COINBASE__API_KEY` (note double underscore), will be accessible as `settings.fetch_ob` and `settings.coinbase.api_key` respectively.

## Usage for Development

```bash
pip install -r requirements.txt
pip install -e .
cd rcd && python rec_data.py
```
