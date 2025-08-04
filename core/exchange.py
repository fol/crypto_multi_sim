from typing import Dict, List, Tuple
from .agent import ActiveAgent
from .message import Message
from ..orderbook.order_book import OrderBook, Order, Trade, MarketData
from ..utils.logger import setup_logger


class ExchangeAgent(ActiveAgent):
    """Exchange agent responsible for maintaining order books and matching orders"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.order_books: Dict[str, OrderBook] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.trade_history: List[Trade] = []
        self.market_data_update_interval = 100  # milliseconds
        self.logger = setup_logger(f"ExchangeAgent.{agent_id}")
    
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
            self.subscribe(f"{symbol}.MARKET_DEPTH")
            # Schedule regular market data updates
            self.schedule_wakeup(self.market_data_update_interval)
    
    def receive_message(self, message: Message):
        """Process incoming messages"""
        if message.topic.endswith(".ORDER"):
            self._process_order(message)
        elif message.topic.endswith(".CANCEL"):
            self._process_cancel(message)
        elif message.topic.endswith(".MARKET_DEPTH"):
            self._process_market_depth_query(message)
        else:
            # Handle other message types
            pass
    
    def _process_order(self, message: Message):
        """Process an order submission"""
        payload = message.payload
        symbol = payload.get("symbol")
        
        self.logger.info(f"[{message.timestamp}ms] Exchange received order: {payload}")
        
        if symbol not in self.order_books:
            self.logger.debug(f"Initializing symbol {symbol}")
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
        
        # Determine if it's a market order (price is infinity for buy or 0 for sell)
        is_market_order = (order.side == "BUY" and order.price == float('inf')) or \
                           (order.side == "SELL" and order.price == 0.0)
        
        # Add order to book and get any trades
        if is_market_order:
            # For market orders, check liquidity with default 80% fill requirement
            can_fill, trades = self.order_books[symbol].add_market_order(order, min_fill_percent=0.8)
            if not can_fill:
                self.logger.info(f"Market order {order.order_id} rejected due to insufficient liquidity")
                return
        else:
            # For limit orders, optionally execute partial market if overlapping with orderbook levels
            # This is controlled by a flag, defaulting to False to maintain backward compatibility
            trades = self.order_books[symbol].add_limit_order(order, execute_partial_market=False)
        
        self.logger.info(f"Order added, {len(trades)} trades generated")
        
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
    
    def _process_market_depth_query(self, message: Message):
        """Process market depth queries from agents"""
        payload = message.payload
        symbol = payload.get("symbol")
        query_type = payload.get("query_type")
        
        if symbol not in self.order_books:
            self.logger.warning(f"Market depth query for unknown symbol: {symbol}")
            return
        
        order_book = self.order_books[symbol]
        response_topic = f"{symbol}.MARKET_DEPTH_RESPONSE"
        response_payload = {"query_type": query_type}
        
        if query_type == "get_market_depth":
            side = payload.get("side")
            depth = payload.get("depth", 5)
            levels = order_book.get_market_depth(side, depth)
            response_payload["levels"] = levels
            
        elif query_type == "get_total_quantity_at_side":
            side = payload.get("side")
            depth = payload.get("depth", None)
            quantity = order_book.get_total_quantity_at_side(side, depth)
            response_payload["quantity"] = quantity
            
        elif query_type == "get_average_price_for_quantity":
            side = payload.get("side")
            quantity = payload.get("quantity")
            avg_price, slippage_bps, fill_percent = order_book.get_average_price_for_quantity(side, quantity)
            response_payload["average_price"] = avg_price
            response_payload["slippage_bps"] = slippage_bps
            response_payload["fill_percentage"] = fill_percent
            
        elif query_type == "can_fill_order":
            side = payload.get("side")
            quantity = payload.get("quantity")
            min_fill_percent = payload.get("min_fill_percent", 1.0)
            can_fill, actual_fill_percent = order_book.can_fill_order(side, quantity, min_fill_percent)
            response_payload["can_fill"] = can_fill
            response_payload["actual_fill_percentage"] = actual_fill_percent
            
        elif query_type == "get_liquidity_score":
            reference_quantity = payload.get("reference_quantity", 100)
            score = order_book.get_liquidity_score(reference_quantity)
            response_payload["liquidity_score"] = score
            
        elif query_type == "get_spread":
            spread = order_book.get_spread()
            response_payload["spread"] = spread
            
        elif query_type == "get_imbalance":
            imbalance = order_book.get_imbalance()
            response_payload["imbalance"] = imbalance
        
        # Send the response back to the querying agent
        self.send_message(response_topic, response_payload, message.timestamp)
    
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