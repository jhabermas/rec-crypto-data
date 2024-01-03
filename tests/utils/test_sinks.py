import pandas as pd
from datetime import datetime, timedelta
from hydra.aggregation.trades import trades_to_ohlcv_pd, generate_ohlcv
from tests.tools.data_generation import generate_trades
from pytest import approx


def test_generate_ohlcv():
    df = pd.DataFrame([{'timestamp': pd.Timestamp('2022-01-01 00:00:00'), 'price': 41000.0, 'amount': 0.1},
                       {'timestamp': pd.Timestamp('2022-01-01 00:01:00'), 'price': 41001.0, 'amount': 0.2}])
    df.set_index('timestamp', inplace=True)
    ohlcv = generate_ohlcv(df)
    assert 'o' in ohlcv.columns
    assert 'h' in ohlcv.columns
    assert 'l' in ohlcv.columns
    assert 'c' in ohlcv.columns
    assert 'v' in ohlcv.columns


def test_trades_to_ohlcv_pd():
    start_time = datetime(2022, 1, 1, 0, 0)
    end_time = datetime(2022, 1, 1, 0, 5)  # Generate for 5 minutes
    freq = timedelta(minutes=1)  # Generate trades every minute
    price_range = (40000, 41000)  # Price between $40,000 and $41,000
    amount_range = (0.1, 1.0)  # Amount between 0.1 and 1.0 BTC
    num_trades = 10  # 10 trades per minute
    random_trades = generate_trades(start_time, end_time, freq, price_range, amount_range, num_trades)

    ohlcv = trades_to_ohlcv_pd(random_trades)
    for index, row in ohlcv.iterrows():
        trades_in_minute = [trade for trade in random_trades if int(index.timestamp() * 1000) <= trade['timestamp'] < int((index + freq).timestamp() * 1000)]
        if trades_in_minute:
            assert row['o'] == trades_in_minute[0]['price']
            assert row['c'] == trades_in_minute[-1]['price']
            assert row['h'] == max(trade['price'] for trade in trades_in_minute)
            assert row['l'] == min(trade['price'] for trade in trades_in_minute)
            assert row['v'] == approx(sum(trade['amount'] for trade in trades_in_minute))

