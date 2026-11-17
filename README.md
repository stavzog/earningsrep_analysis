# Sentiment Analysis on Earnings Calls

We will be making a ANN model to predict whether a company's stock will go up or down based on earnings call data. Our main model will be a GRU that accepts 4-6 calls as input in order to learn the patterns in how tone changes. Then it predicts whether the stock price will increase or decrease.

## Download raw data

Install the loader dependencies and run the script from the project root:

```sh
python -m pip install datasets pandas yfinance pyarrow
python scripts/download_raw_data.py
```

The script saves transcripts and adjusted prices under the Git-ignored
`data/raw/` directory. It requests prices from 2013-12-01 up to (but not
including) 2025-06-01 and includes `RSP`; change the date constants in the
script if needed. It does not clean or label the data.
