from typing import Dict, List, Tuple
from agent import ActiveAgent
from message import Message
from order_book import OrderBook, Order, Trade, MarketData


class ExchangeAgent(ActiveAgent):
    """Exchange agent responsible for maintaining order books and matching orders"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.order_books: Dict[str, OrderBook] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.trade_history: List[Trade] = []
        self.market_data_update_interval = 100  # milliseconds
    
    def initialize_symbol(self, symbol: str):
        """Initialize an order book for a symbol"""
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol)
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                timestamp=0,
                best_bid=0.0,
                best_ask=float('inf')
            )
            # Subscribe to order messages for this symbol
            self.subscribe(f"{symbol}.ORDER")
            self.subscribe(f"{symbol}.CANCEL")
            # Schedule regular market data updates
            self.schedule_wakeup(self.market_data_update_interval)
    
    def receive_message(self, message: Message):
        """Process incoming messages"""
        if message.topic.endswith(".ORDER"):
            self._process_order(message)
        elif message.topic.endswith(".CANCEL"):
            self._process_cancel(message)
        else:
            # Handle other message types
            pass
    
    def _process_order(self, message: Message):
        """Process an order submission"""
        payload = message.payload
        symbol = payload.get("symbol")
        
        print(f"[{message.timestamp}ms] Exchange received order: {payload}")
        
        if symbol not in self.order_books:
            self.initialize_symbol(symbol)
        
        # Create order object
        order = Order(
            order_id=payload.get("order_id"),
            agent_id=message.source_id,
            symbol=symbol,
            side=payload.get("side"),
            price=payload.get("price"),
            quantity=payload.get("quantity"),
            timestamp=message.timestamp
        )
        
        # Add order to book and get any trades
        trades = self.order_books[symbol].add_order(order)
        
        print(f"  Order added, {len(trades)} trades generated")
        
        # Process trades
        for trade_id, price, quantity, buyer_id, seller_id in trades:
            trade = Trade(
                trade_id=trade_id,
                symbol=symbol,
                price=price,
                quantity=quantity,
                buyer_id=buyer_id,
                seller_id=seller_id,
                timestamp=message.timestamp
            )
            
            self.trade_history.append(trade)
            
            # Publish trade execution
            trade_message = Message(
                timestamp=message.timestamp,
                topic=f"{symbol}.TRADE",
                payload={
                    "trade_id": trade_id,
                    "price": price,
                    "quantity": quantity,
                    "buyer_id": buyer_id,
                    "seller_id": seller_id
                },
                source_id=self.agent_id
            )
            self.send_message(trade_message.topic, trade_message.payload, trade_message.timestamp)
        
        # Update market data
        self._update_market_data(symbol, message.timestamp)
        
        # Publish order book update
        orderbook_update = self.order_books[symbol].get_order_book_snapshot()
        orderbook_message = Message(
            timestamp=message.timestamp,
            topic=f"{symbol}.ORDERBOOK",
            payload=orderbook_update,
            source_id=self.agent_id
        )
        self.send_message(orderbook_message.topic, orderbook_message.payload, orderbook_message.timestamp)
    
    def _process_cancel(self, message: Message):
        """Process an order cancellation"""
        payload = message.payload
        symbol = payload.get("symbol")
        order_id = payload.get("order_id")
        
        if symbol in self.order_books:
            cancelled = self.order_books[symbol].cancel_order(order_id)
            if cancelled:
                # Publish cancellation confirmation
                cancel_message = Message(
                    timestamp=message.timestamp,
                    topic=f"{symbol}.CANCEL_CONFIRM",
                    payload={
                        "order_id": order_id,
                        "cancelled": True
                    },
                    source_id=self.agent_id
                )
                self.send_message(cancel_message.topic, cancel_message.payload, cancel_message.timestamp)
                
                # Update market data
                self._update_market_data(symbol, message.timestamp)
    
    def _update_market_data(self, symbol: str, timestamp: int):
        """Update market data for a symbol"""
        if symbol in self.order_books and symbol in self.market_data:
            order_book = self.order_books[symbol]
            market_data = self.market_data[symbol]
            
            market_data.timestamp = timestamp
            market_data.best_bid = order_book.best_bid
            market_data.best_ask = order_book.best_ask
            
            # Publish price update
            price_message = Message(
                timestamp=timestamp,
                topic=f"{symbol}.PRICE",
                payload={
                    "best_bid": market_data.best_bid,
                    "best_ask": market_data.best_ask,
                    "spread": market_data.best_ask - market_data.best_bid if market_data.best_ask != float('inf') else 0
                },
                source_id=self.agent_id
            )
            self.send_message(price_message.topic, price_message.payload, price_message.timestamp)
    
    def wakeup(self, current_time: int):
        """Called by kernel at scheduled intervals"""
        super().wakeup(current_time)
        
        # Publish market statistics
        self._publish_market_statistics(current_time)
        
        # Schedule next wakeup
        self.schedule_wakeup(current_time + self.market_data_update_interval)
    
    def _publish_market_statistics(self, timestamp: int):
        """Publish market statistics"""
        for symbol, market_data in self.market_data.items():
            # Calculate volume and VWAP from recent trades
            recent_trades = [
                trade for trade in self.trade_history 
                if trade.timestamp >= timestamp - self.market_data_update_interval and trade.symbol == symbol
            ]
            
            total_volume = sum(trade.quantity for trade in recent_trades)
            vwap = 0.0
            if total_volume > 0:
                total_value = sum(trade.price * trade.quantity for trade in recent_trades)
                vwap = total_value / total_volume
            
            stats_message = Message(
                timestamp=timestamp,
                topic=f"{symbol}.STATS",
                payload={
                    "volume": total_volume,
                    "vwap": vwap,
                    "best_bid": market_data.best_bid,
                    "best_ask": market_data.best_ask
                },
                source_id=self.agent_id
            )
            self.send_message(stats_message.topic, stats_message.payload, stats_message.timestamp)