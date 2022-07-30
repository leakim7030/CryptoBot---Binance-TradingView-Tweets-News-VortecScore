# CryptoBot---Binance-TradingView-Tweets-News-VortecScore

The bot works like this: 

1. You set it up to trade with X usd in equity
2. You receive signals from tradingview(requires you to make them, or use someone elses). e.G you get a buy signal on BTC from the technical analysis on tradingview.
3. The bot then scans twitter and news headlines from the websites found in crypto feeds.csv and performs a sentiment analysis on those.
It also uses the vortec score from cointelegraph, which in my opinion a waste of money to use, it would be better to gather more data sources, such as reddit, 
blockchain data etc.

4. The bot executes a buy order if the sentiment score is above a set threshold, say  0,5 and the current sentiment score is 0,55 
the amount spend on btc is:

equity = 1000 usd
current_price_btc = 23000 usd
quantity to buy = (equity/10*0,55) / current_price_btc = 0,00239

which is 55 usd

This functionality was added by the assumption that if there is an overall positive sentiment, the technical signal should be solid. 

5. in order to execute a buy/sell order you need to setup api-keys from binance


You can run the bot with Flask, using a local server, you also need to setup to allow for TradingView alerts, I use Ngrok.
The bot sends telegram messages and is operatable with commands in telegram.

To setup the JSON messages from tradingview you need to format the message exactly like this 

{ "passphrase": "Your passphrase here", "time": "{{timenow}}", "exchange": "{{exchange}}", "symbol": "{{ticker}}", "quantity": 1.0, "side": "{{strategy.order.action}}", "type": "LIMIT", "timeInForce": "GTC", "currentPrice": {{close}} }



