import json, config
import datetime
import threading
import nltk
import re
from bs4 import BeautifulSoup
from textblob import TextBlob
import snscrape.modules.twitter as sntwitter
import xml.etree.ElementTree as ET
import requests
import csv
import numpy as np
from nltk.sentiment import SentimentIntensityAnalyzer
from bot import MainBot
from binance_functions import Binance
from message_filter_functions import *
from flask import Flask, request



nltk.download('vader_lexicon')

tweets = []  # to be added by processes
comp_twitter_values = []  ##list of all the compound twitter sentiments


def percentage(part, whole):
    percentage = 100 * float(part) / float(whole)
    return str(percentage) + "%"


with open('C:/Users/Eier/Desktop/TradingView-Binance-Telegram-Bot-main/Crypto feeds.csv') as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader, None)
    feeds = []
    for row in csv_reader:
        feeds.append(row[0])


def get_headlines():
    '''Returns the last headline for each link in the CSV file'''
    # add headers to the request for ElementTree. Parsing issues occur without headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'
    }

    proccesses = []
    crypto_feeds_csv = []
    threads_news = 15
    num_feeds = len(feeds)
    for r in range(0, num_feeds, int(round(num_feeds / threads_news))):
        crypto_feeds_csv.append(r)
    if len(crypto_feeds_csv) <= threads_news + 1:
        for f in crypto_feeds_csv:
            x = f + int(num_feeds / threads_news)
            p = threading.Thread(target=feeds_scraper, args=(f, x))
            proccesses.append(p)
        for p in proccesses:
            p.start()
        for p in proccesses:
            p.join()

    else:
        print("Error: Check how many keywords that are passed to func get_headlines(), has to be 15 or less")
    return headlines


def feeds_scraper(f, x):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'
    }
    for feed in feeds[f:x]:
        try:
            # grab the XML for each RSS feed
            r = requests.get(feed, headers=headers, timeout=7)

            # define the root for our parsing
            root = ET.fromstring(r.text)

            # identify the last Headline
            channel = root.find('channel/item/title').text
            pubDate = root.find('channel/item/pubDate').text

            # append the source and the title
            headlines['source'].append(feed)

            # append the publication date
            headlines['pubDate'].append(pubDate)

            # some jank to ensure no alien characters are being passed
            headlines['title'].append(channel.encode('UTF-8').decode('UTF-8'))

        except:
            pass
            #print(f'Could not parse {feed}')


def categorise_headlines():
    '''arrange all headlines scaped in a dictionary matching the coin's name'''
    # get the headlines
    headlines = get_headlines()
    categorised_headlines = {}

    # this loop will create a dictionary for each keyword defined
    for keyword in keywords:
        categorised_headlines['{0}'.format(keyword)] = []

    # keyword needs to be a loop in order to be able to append headline to the correct dictionary
    for keyword in keywords:

        # looping through each headline is required as well
        for headline in headlines['title']:

            # appends the headline containing the keyword to the correct dictionary
            if any(key in headline for key in keywords[keyword]):
                categorised_headlines[keyword].append(headline)

    return categorised_headlines


def analyse_headlines():
    '''Analyse categorised headlines and return NLP scores'''
    sia = SentimentIntensityAnalyzer()
    categorised_headlines = categorise_headlines()

    sentiment = {}

    for coin in categorised_headlines:
        if len(categorised_headlines[coin]) > 0:
            # create dict for each coin
            sentiment['{0}'.format(coin)] = []
            # append sentiment to dict
            for title in categorised_headlines[coin]:
                sentiment[coin].append(sia.polarity_scores(title))

    return sentiment


def compile_sentiment():
    '''Arranges every compound value into a list for each coin'''
    sentiment = analyse_headlines()
    compiled_sentiment = {}

    for coin in sentiment:
        compiled_sentiment[coin] = []

        for item in sentiment[coin]:
            # append each compound value to each coin's dict
            compiled_sentiment[coin].append(sentiment[coin][sentiment[coin].index(item)]['compound'])

    return compiled_sentiment


def compound_average():
    '''Calculates and returns the average compoud sentiment for each coin'''
    compiled_sentiment = compile_sentiment()
    headlines_analysed = {}

    for coin in compiled_sentiment:
        headlines_analysed[coin] = len(compiled_sentiment[coin])

        # calculate the average using numpy if there is more than 1 element in list
        compiled_sentiment[coin] = np.array(compiled_sentiment[coin])

        # get the mean
        compiled_sentiment[coin] = np.mean(compiled_sentiment[coin])

        # convert to scalar
        compiled_sentiment[coin] = compiled_sentiment[coin].item()

    return compiled_sentiment  # , headlines_analysed


def compound_news():
    '''Check if the sentiment is positive and keyword is found for each handle'''
    compounded_news = compound_average()
    return compounded_news


def func_comp_twitter(comp_twitter):
    comp_twitter_values.append(comp_twitter)
    return comp_twitter_values


def get_tweets(keyword, noOfTweet):
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(f'{keyword} since:{datetime.date.today()}').get_items()):
        if i > noOfTweet:
            break
        if tweet.likeCount >= 1 or tweet.replyCount >= 1:
            tweets.append(tweet.content)


def run_sentiment_twitter(list_keywords, noOfTweet):
    proccesses = []
    ##starting multithreading, from different keywords, don't add too many threads, for stability.
    if len(list_keywords) <= 15:
        for a in list_keywords:
            p = threading.Thread(target=get_tweets, args=(a, noOfTweet))
            proccesses.append(p)
        for p in proccesses:
            p.start()
        for p in proccesses:
            p.join()
    else:
        print("Error: Check how many keywords that are passed to func run_sentiment_twitter(), has to be 16 or less")
    polarity = 0
    tweet_list = []
    compounding_score = []
    set(tweets)
    list(tweets)
    for tweet in tweets:
        tweet_list.append(tweet)
        analysis = TextBlob(tweet)
        score = SentimentIntensityAnalyzer().polarity_scores(tweet)
        comp = score['compound']
        polarity += analysis.sentiment.polarity
        compounding_score.append(comp)
    try:
        comp = sum(compounding_score) / len(tweet_list)
        tweets.clear()
        return comp
    except ZeroDivisionError:
        print("Zero division error, Failed to gather tweets, to calculate compounding_score")
        tweets.clear()
        comp = 0.0
        return comp


headlines = {'source': [], 'title': [], 'pubDate': []}
comp_list_running = dict.fromkeys(["News", "Twitter"])
news_list = []
twitter_list = []
noOfTweet = 2000
# int, how many tweets to gather

#WHICH Crypto coins you want to trade, need to setup tradingview to generate signals for all the coins
keywords = {
    'XRP': ['#ripple', 'XRP', 'XRP', 'Ripple', 'xrp'],
    'BTC': ['#BTC', 'BITCOIN', 'Bitcoin', 'bitcoin'],
    'XLM': ['#Stellar Lumen s', 'XLM', 'xlm','stellar'],
    'BCH': ['#Bitcoin Cash', 'BCH','bitcoincash'],
    'ETH': ['#ETH', 'Ethereum', 'ethereum'],
    #'BNB': ['#BNB', 'Binance Coin'],  # added
    'LTC': ['#LTC', 'Litecoin', 'ltc','litecoin'],
    'AVAX': ['#AVAX', 'Avalanche', 'AVALANCHE', 'Avax','avalanche'],
    'SOL': ['#SOL', 'SOLANA', 'sol', 'Sol', 'Solana','solana'],
    'ADA': ['#ADA', 'CARDANO', 'ada', 'Cardano', 'Ada','cardano'],
    'DOT': ['#DOT', 'POLKADOT', 'dot', 'Polkadot', 'Dot','polkadot'],
    'MATIC': ['#MATIC', 'POLYGON', 'matic', 'polygon', 'Matic', 'Polygon','maticnetwork'],
    'EGLD': ['#EGLD', 'ELROND', 'egld', 'elrond', 'Egld', 'Elrond','elrond'],
    'ALGO': ['#ALGO', 'ALGORAND', 'algo', 'Algo', 'Algorand', 'algorand'],
    'SAND': ['#SAND', 'THE SANDBOX', 'sand', 'the sandbox', 'Sand', 'The Sandbox', 'thesandbox'],
    'MANA': ['#MANA', 'DECENTRALAND', 'Mana', 'Decentraland', 'mana', 'decentraland'],
    'ATOM': ['#ATMOM', 'COSMOS', 'Atom', 'Cosmos', 'atom', 'cosmos'],
    'THETA': ['#THETA', 'theta', 'Theta','thetatoken'],
    'ICP': ['#ICP', 'Internet Computer', 'INTERNET COMPUTER','internetcomputer'],
    'AXS': ['#AXS', 'AXIE INFINITY', 'Axie Infinity','axieinfinity'],
    'LINK': ['#LINK', 'CHAINLINK', 'link', 'chainlink'],
    'UNI': ['#UNI', 'UNISWAP', 'uni', 'Uniswap','uniswap'],
    'LUNA': ['#LUNA', 'TERRA', 'Terra', 'terra', 'luna'],
    'VET': ['#VET', 'VeChain', 'VECHAIN', 'vechain'],
    'FTT': ['#FTT', 'FTX Token', 'FTX TOKEN', 'ftt','ftxtoken'],
    'HBAR': ['#HBAR', 'Hedera', 'HEDERA', 'hbar','hederahashgraph'],
    'HNT': ['#HNT', 'Helium', 'HELIUM', 'hnt', 'helium'],
    'FLOW': ['#FLOW', 'Flow', 'flow', 'flowdapperlabs'],
    'KLAY': ['#KLAY', 'Klaytn', 'klay', 'KLAYTN', 'klaytn'],
    'AAVE': ['#AAVE', 'Aave', 'aave'],
    'CAKE': ['#CAKE', 'PancakeSwap', 'PANCAKESWAP', 'Pancakeswap','pancakeswap'],
    'ENJ': ['#ENJ', 'Enjin Coin', 'enjin coin', 'enj', 'enjincoin'],
    'ONE': ['#ONE', 'Harmony', 'HARMONY', 'one', 'harmony'],
    'ZEC': ['#ZEC', 'Zcash', 'ZCASH', 'zec', 'zcash'],
    'GALA': ['#GALA', 'Gala', 'gala'],
    'MKR': ['#MKR', 'MAKER', 'mkr', 'Maker', 'maker'],
    'RUNE': ['#RUNE', 'THORChain', 'Thorchain', 'rune', 'Rune', 'thorchain'],
    'KSM': ['#KSM', 'Kusama', 'KUSAMA', 'kusama', 'kusamacoin'],
    'QNT': ['#QNT', 'Quant', 'qnt', 'QUANT', 'quant'],
    'NEO': ['#NEO', 'Neo', 'neo'],
    'STX': ['#STX', 'Stacks', 'STACKS', 'stx', 'blockstack'],
    'CHZ': ['#CHZ', 'Chiliz', 'CHILIZ', 'chz', 'chiliz'],
    'HOT': ['#HOT coin', 'Holo', 'HOLO', 'holo', 'hot coin','holochain'],
    'WAVES': ['#WAVES', 'Waves', 'waves'],
    'CRV': ['#CRV', 'Curve DAO Token', 'CURVE DAO TOKEN', 'curve dao token','curve'],
    'BTT': ['#BTT', 'BitTorrent', 'BITTORRENT', 'btt', 'bittorrent'],
    'DASH': ['#DASH', 'Dash', 'dash'],
    'AR': ['#AR', 'Arweave', 'ARWEAVE', 'arweave'],
    'CELO': ['#CELO', 'Celo', 'celo'],
    'IOTX': ['#IOTX', 'IoTex', 'Iotex', 'iotx', 'iotex'],
    'TFUEL': ['#TFUEL', 'Theta Fuel', 'tfuel', 'theta fuel', 'Tfuel', 'thetafuel'],
    'XEM': ['#XEM', 'NEM', 'xem', 'nem'],
    'DCR': ['#DCR', 'Decred', 'dcr', 'decred'],
    'QTUM': ['#QTUM', 'Qtum', 'qtum'],
    'ICX': ['#ICX', 'ICON', 'icx', 'Icx','icon'],
    'ZEN': ['#ZEN', 'Horizen', 'HORIZEN', 'horizen'],
    'AUDIO': ['#AUDIO', 'Audius', 'AUDIUS', 'audius'],
    'OMG': ['#OMG', 'OMG Network', 'Omg Network', 'OMG NETWORK', 'omisego'],
    'VGX': ['#VGX', 'Voyager Token', 'vgx', 'VOYAGER TOKEN', 'voyager token','voyagertoken'],
    'RVN': ['#RVN', 'Ravencoin', 'RAVENCOIN', 'rvn', 'ravencoin'],  # added
    'ZIL': ['#ZIL', 'zil', 'Zilliqa', 'ZILLIQA', 'zilliqa'],
    'NEAR': ['#NEAR', 'NEAR Protocol', 'near protocol', 'NEAR PROTOCOL', 'nearprotocol'],
    'AMP': ['#AMP', 'amp', 'amp crypto', 'synereo'],
    'HIVE': ['#Hive', 'Hive social', 'Hive crypto', 'HIVE', 'hive coin'],
    'IOTA': ['#IOTA', 'MIOTA', 'miota', 'Iota', 'iota'],
    'XTZ': ['#XTZ', 'Tezos', 'xtz', 'TEZOS', 'tezos'],
    'FTM': ['#FTM', 'Fantom', 'FANTOM', 'ftm','fantom'],
    'XMR': ['#XMR', 'Monero', 'MONERO', 'xmr', 'monero'],
    'LRC': ['#LRC', 'Loopring', 'lrc', 'LOOPRING', 'loopring'],
    'GRT': ['#GRT', 'The graph', 'grt', 'The Graph','thegraph'],
    'COMP': ['#COMP', 'Compound', 'comp', 'COMPOUND', 'compound'],
    'ANKR':['#ANKR','Ankr','Anker', 'ankrnetwork'],
    'SC':['#SC','Siacoin','SC', 'siacoin'],
    'LPT':['#LPT','Livepeer','LPT', 'livepeer'],
    'STORJ':['#STORJ','Storj','STORJ', 'storj'],
    'ROSE':['#ROSE','Oasis Network', 'oasisnetwork'],
    'ZRX':['#ZRX','ZRZ','0x'],
    'PERP':['#PERP','PERP','Perpetual Protocol', 'perpetualprotocol'],
    'BNT':['#BNT','Bancor','BNT','bancor'],
    'SNX':['#SNX', 'Synthetix', 'synthetixnetworktoken'],
    'POLY':['#POLY', 'Polymath', 'polymath'],
    'FIS':['#FIS','Stafi'],
    'MIR':['#MIR','Mirror Protocol', 'mirrorprotocol'],
    '1INCH':['#1INCH','1inch Network', '1inch'],
    'NULS':['#NULS','NULS','nuls','Nuls'],
    'ORN':['#ORN', 'Orion Protocol', 'orionprotocol'],
    'BZRX':['#BZRX','bZx Protocol'],
    'POND':['#POND','Marlin'],
    'PERL':['#PERL','PERL.eco','Perlin', 'perlin'],
    'NANO':['#NANO','Nano', 'nano'],
    'CTK':['#CTK','CTK','CertiK', 'Certik', 'certik'],
    'PNT':['#PNT','PNT','pNetwork', 'pnetwork'],
    'WTC':['#WTC','WTC','Waltonchain', 'waltonchain'],
    'UMA':['#UMA','UMA','uma'],
    'WAN':['#WAN', 'Wanchain', 'wanchain'],
    'SYS':['#SYS', 'Sys', 'Syscoin', 'syscoin'],
    'LSK':['#LSK', 'LSK', 'Lisk', 'lisk'],
    'FIO':['#FIO','FIO','FIO Protocol'],
    'RARE':['#RARE', 'SuperRare', 'superrare', 'SUPERRARE'],
    'DGB':['#DGB', 'DigiByte', 'digibyte'],
    'CHESS':['#CHESS','Tranchess', ' chess crypto'],
    'DF':['#DF', 'dForce', 'dforce', 'DFORCE'],
    'MOVR':['#MOVR', 'Moonriver', 'MOONRIVER'],
    'ELF':['#ELF', 'aelf',' elf crypto'],
    'OXT':['#OXT', 'Orchid', 'orchidcrypto'],
    'KEEP':['#KEEP', 'Keep Network', 'keepnetwork'],
    'ANT':['#ANT', 'Aragon', 'aragon'],
    'REP':['#REP', 'Augur', 'augur'],
    'BADGER':['#BADGER', 'Badger DAO', 'badgerdao'],
    'BAKE':['#BAKE', 'BakeryToken', 'bakerytoken'],
    'BAL':['#BAL', 'Balancer Coin', 'balancercoin'],
    'BAND':['#BAND', 'Band Protocol', 'bandprotocol'],
    'BOND':['#BOND', 'BarnBridge', 'barnbridge'],
    'FIDA':['#FIDA', 'Bonfida', 'bonfida'],
    'COTI':['#COTI','coti'],
    'SUSHI':['#SUSHI', 'sushi'],
    'SHIB':['#SHIB', 'SHIBA INU', 'shibainu'],
    'DOGE':['#DOGE', 'Dogecoin', 'dogecoin'],
    'REQ':['#REQ', 'Request Network', 'requestnetwork'],
    'SKL':['#SKL', 'SKALE Network', 'skalenetwork'],
    'SFP':['#SFP', 'SafePal', 'safepal'],
    'SRM':['#SRM', 'Serum', 'serum'],
    'TRB':['#TRB', 'Tellor', 'tellor'],
    'TORN':['#TORN', 'Tornado Cash', 'tornadocash'],
    'CVP':['#CVP', 'PowerPool', 'powerpool'],
    'FLM':['#FLM', 'flamingo'],
    'DNT':['#DNT', 'district0x'],
    'FUN':['#FUN', 'funfair'],
    'KP3R':['#KP3R', 'keep3rv1'],
    'NMR':['#NMR', 'numeraire'],
    'TOMO':['#TOMO', 'tomochain'],
    'MFT':['#MFT', 'Hifi Finance', 'mainframe'],
    'AKRO':['#AKRO', 'akropolis'],
    'IRIS':['#IRIS', 'irisnet'],
    'LIT':['#LIT', 'litentry'],
    'DODO':['#DODO', 'dodo'],
    'WIN':['#WIN', 'wink'],
    'KAVA':['#KAVA', 'kavaio'],
    'ONT':['#ONT', 'ontology'],
    'TVK':['#TVK', 'terravirtuakolect'],
    'KNC':['#KNC', 'kybernetwork'],
    'GNO':['#GNO', 'gnosis'],
    'KMD':['#KMD', 'komodo'],
    'FET':['#FET', 'fetch'],
    'RAY':['#RAY', 'raydium'],
    'ALICE':['#ALICE', 'myneighboralice'],
    'GHST':['#GHST', 'Aavegotchi'],
    'DAR':['#DAR', 'Mines of Dalarnia'],
    'SLP':['#SLP',' Smooth Love Potion'],
    'ILV':['#ILV', 'Illuvium'],
    'PYR':['#PYR', 'Vulcan Forged PYR'],
    'MC':['#MC', 'Merit circle']

}


def quantity_buy(symbol_x,current_price, equity, sentiment, client):
    if type(sentiment) == float:
      #  if float(sentiment) > 0.70:

        if float(((equity / 10) * sentiment) / current_price) >= 1:
            quantity = float(((equity / 10) * sentiment) / current_price)
            quantity = int(np.around(quantity))
            print(f"Buying {quantity} {symbol_x} for {current_price * quantity}USDT")
            return quantity

        elif float(((equity / 10) * sentiment) / current_price) < 1:
            quantity = float(((equity / 11) * sentiment) / current_price)
            b = str(quantity)
            print(b)
            i = 0
            for c in b[2::1]:
                print(c)
                i += 1
                if c != "0":
                    break

            quantity = np.around(quantity, decimals=i)
            if quantity > 0.0:
                print(f"Buying {quantity} {symbol_x} for {current_price * quantity}USDT")
            else:
                pass

            sell_quantity_input = client.get_asset_balance(asset=symbol_x)
            sell_quantity = sell_quantity_input["free"]

            if float(sell_quantity) == 0.0000: #check to see if wallet is empty before making a purchase

                return quantity

        # if (float(sentiment) > 0.50) and (float(sentiment) < 0.71):
        #
        #     if float(((equity / 10) * 0.40) / current_price) >= 1:
        #         quantity = float(((equity / 10) * 0.4) / current_price)
        #         quantity = int(np.around(quantity))
        #         print(f"Buying {quantity} {symbol_x} for {current_price * quantity}USDT")
        #         return quantity
        #
        #     elif float(((equity / 10) * 0.40) / current_price) < 1:
        #         quantity = float(((equity / 11) * 0.4) /current_price)
        #         b = str(quantity)
        #         print(b)
        #         i = 0
        #         for c in b[2::1]:
        #             print(c)
        #             i += 1
        #             if c != "0":
        #                 break
        #
        #         quantity = np.around(quantity, decimals=i)
        #         print(f"Buying {quantity} {symbol_x} for {current_price * quantity}USDT")
        #         return quantity

   # else:
        # if float(((equity / 10) * 0.11) / current_price) >= 1:
        #     quantity = float(((equity / 10) * 0.11) / current_price)
        #     quantity = int(np.around(quantity))
        #     print(f"Buying {quantity} {symbol_x} for {current_price * quantity}USDT")
        #     return quantity
        #
        # elif float(((equity / 10) * 0.11) / current_price) < 1:
        #     quantity = float(((equity / 11) * 0.11) / current_price)
        #     b = str(quantity)
        #     print(b)
        #     i = 0
        #     for c in b[2::1]:
        #         print(c)
        #         i += 1
        #         if c != "0":
        #             break
        #
        #     quantity = np.around(quantity, decimals=i)
            print(f"Sentiment value of : {sentiment} is too low, needs to be above 0.6 ")
        #    return quantity



def social_sentiment(arg):
    vortec_score_current = vortec_score(keywords[arg][-1])
    #if (vortec_score_current >= 0.49):
    news_list_current = compound_news().get(arg)
    twitter_list_current = run_sentiment_twitter(keywords[arg], noOfTweet)

    if news_list_current != None:

        s_sentiment = (news_list_current + twitter_list_current + vortec_score_current) / 3
        return s_sentiment
    elif twitter_list_current != 0:
        s_sentiment = (twitter_list_current + vortec_score_current) / 2
        return s_sentiment
    else:
        return vortec_score_current
    # else:
    #     sentiment_zero = 0.0
    #     return sentiment_zero

# def sell_coin():
#     return


def vortec_score(coin):
    try:
        ## need to refresh cookie every x days(28?) also needs to get the cookie, e.G be a paying subscriber
        cookies = {'remember_user_token':
                       ''}
        input_search = coin  # special formatting, check https://pro.cointelegraph.com/coins/
        string_a = f'{input_search}","sentigrade":"'
        response = requests.get(f"https://pro.cointelegraph.com/coins/{input_search}", cookies=cookies)
        soup = BeautifulSoup(response.text, "html.parser")
        test_c = str(soup)
        stripped_c = test_c.strip()
        match = re.search(string_a, stripped_c)
        index_vortec = slice(match.span()[1], match.span()[1] + 2, 1)
        vortec_score = test_c[index_vortec]
        vortec_sentiment = int(vortec_score) / 100

        return vortec_sentiment
    except:
        print('No vortec score, be careful.')
        vortec_sentiment = 0.0
        return vortec_sentiment


app = Flask(__name__)
bot = MainBot()  # Handles all telegram communication


## ---- RECEIVE TRADINGVIEW WEBHOOK AND PLACE ORDER ---- ##
@app.route('/', methods=['POST'])  ## måtte endre fra '/botwebhook' til '/'
def webhook_process():
    client = Binance(config.SPOTTEST_API_KEY, config.SPOTTEST_SECRET_KEY)
    equity = 1000  # CASH USD to be spent trading
    if bot.block_tradingview:
        bot.message("An order from TradingView has been blocked")
    else:
        data = json.loads(request.data)  # Grabs JSON data sent from TradingView via webhook
        if data["passphrase"] == config.PASSPHRASE:
            symbol = data['symbol']
            type = data['type']
            side = data['side'].upper()
            price = data['currentPrice']
            timeInForce = data['timeInForce']
            symbol_x = symbol.replace("USDT", "")

            if side == "BUY":

                s_sentiment = social_sentiment(symbol_x)
                quantity = quantity_buy(symbol_x,price, equity, s_sentiment, client)
                if quantity > 0.00:
                    if type == 'MARKET':
                        order_response = client.market_order(symbol, side, type, quantity)
                    elif type == 'LIMIT':
                        print(symbol, side, type, timeInForce, quantity, price)
                        order_response = client.limit_order(symbol, side, type, timeInForce, quantity, price)
                    if order_response:
                        order_confirmation = order_message(order_response)  # Create a confirmation message w/ order details
                        bot.message(order_confirmation)  # Sends confirmation message via Telegram
                        return {
                            'code': 'success'
                        }
                    else:
                        # bot.error_message(tradingview_symbol, tradingview_quantity, "Denied") #Sends error mesage to admin of Telegram bot
                        return {
                            'code': "failed",
                            'message': "Check console log for error"
                        }
                else:
                    print(f"Sentiment is too low to complete purchase order for {symbol_x}.")
                    # bot.message(f"Received sell alert, but no coins in {symbol_x} wallet to sell.")  # Sends confirmation message via Telegram
                    return {
                        'code': 'success'
                    }

            elif side == "SELL":
                sell_quantity_input = client.get_asset_balance(asset=symbol_x)
                sell_quantity = sell_quantity_input["free"]


                if float(sell_quantity) > 0.0000:

                    if type == 'MARKET':
                        #print(f"Selling {sell_quantity} {symbol_x} for {price * sell_quantity} USDT")
                        order_response = client.market_order(symbol, side, type, sell_quantity)
                    elif type == 'LIMIT':
                        #print(symbol, side, type, timeInForce, sell_quantity, price)
                        order_response = client.limit_order(symbol, side, type, timeInForce, sell_quantity, price)
                    if order_response:
                        order_confirmation = order_message(order_response)  # Create a confirmation message w/ order details
                        bot.message(order_confirmation)  # Sends confirmation message via Telegram
                        return {
                            'code': 'success'
                        }
                    else:
                        # bot.error_message(tradingview_symbol, tradingview_quantity, "Denied") #Sends error mesage to admin of Telegram bot
                        return {
                            'code': "failed",
                            'message': "Check console log for error"
                        }
                else:
                    print(f"Received sell alert, but no coins in {symbol_x} wallet to sell.")
                    #bot.message(f"Received sell alert, but no coins in {symbol_x} wallet to sell.")  # Sends confirmation message via Telegram
                    return {
                        'code': 'success'
                    }
            else:
                    print(f'Message has to contain - "side": "BUY" | OR | "side": "SELL" ')




        else:
            bot.message("An unauthorized order from TradingView has been blocked. Check your security")


if __name__ == "__main__":
    app.run()
