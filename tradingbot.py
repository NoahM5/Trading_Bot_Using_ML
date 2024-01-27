import alpaca_trade_api as trade_api
from datetime import timedelta, datetime
from lumibot import brokers as lb_brokers
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies import Strategy
from lumibot import Trader
from sentiment_analysis import analyze_sentiment

# Alpaca API configuration
API_KEY = "YOUR API KEY"
API_SECRET = "YOUR API SECRET"
API_ENDPOINT = "https://paper-api.alpaca.markets"

ALPACA_CONFIG = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "USE_PAPER": True
}

class AutomatedTrader(Strategy):
    def setup(self, trade_symbol="SPY", risk_factor=0.5):
        self.trade_symbol = trade_symbol
        self.sleep_duration = "1D"  # 24 hours
        self.previous_trade = None
        self.risk_factor = risk_factor
        self.trade_api = trade_api.REST(base_url=API_ENDPOINT, key_id=API_KEY, secret_key=API_SECRET)

    def calculate_position(self):
        account_balance = self.get_balance()
        current_price = self.get_current_price(self.trade_symbol)
        trade_amount = round(account_balance * self.risk_factor / current_price, 0)
        return account_balance, current_price, trade_amount

    def determine_dates(self):
        current_date = self.get_current_datetime()
        date_three_days_ago = current_date - timedelta(days=3)
        return current_date.strftime('%Y-%m-%d'), date_three_days_ago.strftime('%Y-%m-%d')

    def evaluate_sentiment(self):
        current_date, past_date = self.determine_dates()
        recent_news = self.trade_api.get_news(self.trade_symbol, start=past_date, end=current_date)
        headlines = [item.__dict__["_raw"]["headline"] for item in recent_news]
        sentiment_prob, sentiment_value = analyze_sentiment(headlines)
        return sentiment_prob, sentiment_value

    def on_market_iteration(self):
        balance, price, amount = self.calculate_position()
        sentiment_prob, sentiment = self.evaluate_sentiment()

        if balance > price:
            if sentiment == "positive" and sentiment_prob > 0.999:
                if self.previous_trade == "sell":
                    self.close_all_positions()
                order = self.generate_order(
                    self.trade_symbol,
                    amount,
                    "buy",
                    order_type="bracket",
                    profit_target=price * 1.20,
                    stop_loss=price * 0.95
                )
                self.execute_order(order)
                self.previous_trade = "buy"
            elif sentiment == "negative" and sentiment_prob > 0.999:
                if self.previous_trade == "buy":
                    self.close_all_positions()
                order = self.generate_order(
                    self.trade_symbol,
                    amount,
                    "sell",
                    order_type="bracket",
                    profit_target=price * 0.80,
                    stop_loss=price * 1.05
                )
                self.execute_order(order)
                self.previous_trade = "sell"

begin_date = datetime(2020, 1, 1)
finish_date = datetime(2023, 12, 31)
broker = lb_brokers.Alpaca(ALPACA_CONFIG)
automated_strategy = AutomatedTrader(name='AutoTradeStrategy', broker=broker, 
                                     parameters={"trade_symbol": "SPY", "risk_factor": 0.5})
automated_strategy.backtest(
    YahooDataBacktesting,
    begin_date,
    finish_date,
    parameters={"trade_symbol": "SPY", "risk_factor": 0.5}
)