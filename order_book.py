from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from sortedcontainers import SortedDict
import heapq


@dataclass
class Order:
    """Represents a single order in the order book"""
    order_id: str
    agent_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    price: float
    quantity: int
    timestamp: int
    
    def __post_init__(self):
        if self.side not in ["BUY", "SELL"]:
            raise ValueError("Side must be 'BUY' or 'SELL'")


@dataclass
class OrderBookLevel:
    """Represents a price level in the order book"""
    price: float
    quantity: int = 0
    orders: List[Order] = field(default_factory=list)


class OrderBook:
    """Limit order book implementation for a single symbol"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        # Bids sorted in descending order (highest price first)
        self.bids = SortedDict(lambda x: -x)  # price -> OrderBookLevel
        # Asks sorted in ascending order (lowest price first)
        self.asks = SortedDict()  # price -> OrderBookLevel
        self.best_bid = 0.0
        self.best_ask = float('inf')
        self.order_map: Dict[str, Order] = {}  # order_id -> Order
    
    def add_order(self, order: Order) -> List[Tuple[str, float, int, str, str]]:
        """Add an order to the book and return any trades generated"""
        # Store order for later lookup
        self.order_map[order.order_id] = order
        
        # Get or create the price level
        if order.side == "BUY":
            if order.price not in self.bids:
                self.bids[order.price] = OrderBookLevel(order.price)
            level = self.bids[order.price]
        else:  # SELL
            if order.price not in self.asks:
                self.asks[order.price] = OrderBookLevel(order.price)
            level = self.asks[order.price]
        
        # Add order to the level
        level.orders.append(order)
        level.quantity += order.quantity
        
        # Update best prices
        self._update_best_prices()
        
        # Try to match the order
        return self._match_order(order)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID"""
        if order_id not in self.order_map:
            return False
        
        order = self.order_map[order_id]
        
        # Remove from price level
        if order.side == "BUY":
            if order.price in self.bids:
                level = self.bids[order.price]
                level.orders = [o for o in level.orders if o.order_id != order_id]
                level.quantity -= order.quantity
                if level.quantity <= 0:
                    del self.bids[order.price]
        else:  # SELL
            if order.price in self.asks:
                level = self.asks[order.price]
                level.orders = [o for o in level.orders if o.order_id != order_id]
                level.quantity -= order.quantity
                if level.quantity <= 0:
                    del self.asks[order.price]
        
        # Remove from order map
        del self.order_map[order_id]
        
        # Update best prices
        self._update_best_prices()
        
        return True
    
    def _match_order(self, order: Order) -> List[Tuple[str, float, int, str, str]]:
        """Match an order against the opposite side of the book"""
        trades = []
        
        if order.side == "BUY":
            # Match against asks (lowest prices first)
            while (order.quantity > 0 and self.asks and 
                   self.asks.peekitem(0)[0] <= order.price):
                ask_price, ask_level = self.asks.peekitem(0)
                trades.extend(self._execute_match(order, ask_level))
                if ask_level.quantity <= 0:
                    del self.asks[ask_price]
        else:  # SELL
            # Match against bids (highest prices first)
            while (order.quantity > 0 and self.bids and 
                   self.bids.peekitem(0)[0] >= order.price):
                bid_price, bid_level = self.bids.peekitem(0)
                trades.extend(self._execute_match(order, bid_level))
                if bid_level.quantity <= 0:
                    del self.bids[bid_price]
        
        # Update best prices after matching
        self._update_best_prices()
        
        return trades
    
    def _execute_match(self, incoming_order: Order, 
                      opposite_level: OrderBookLevel) -> List[Tuple[str, float, int, str, str]]:
        """Execute matches between an incoming order and orders at a level"""
        trades = []
        
        # Process orders at this level in time priority (FIFO)
        i = 0
        while i < len(opposite_level.orders) and incoming_order.quantity > 0:
            existing_order = opposite_level.orders[i]
            
            # Determine trade quantity (minimum of both orders)
            trade_quantity = min(incoming_order.quantity, existing_order.quantity)
            
            # Create trade record
            trade = (
                f"TRADE_{incoming_order.order_id}_{existing_order.order_id}",
                existing_order.price,  # Use existing order price for execution
                trade_quantity,
                incoming_order.agent_id,
                existing_order.agent_id
            )
            trades.append(trade)
            
            # Update quantities
            incoming_order.quantity -= trade_quantity
            existing_order.quantity -= trade_quantity
            opposite_level.quantity -= trade_quantity
            
            # Remove fully executed orders
            if existing_order.quantity <= 0:
                del self.order_map[existing_order.order_id]
                del opposite_level.orders[i]
            else:
                i += 1
        
        return trades
    
    def _update_best_prices(self):
        """Update the best bid and ask prices"""
        self.best_bid = self.bids.peekitem(0)[0] if self.bids else 0.0
        self.best_ask = self.asks.peekitem(0)[0] if self.asks else float('inf')
    
    def get_order_book_snapshot(self, depth: int = 5) -> Dict[str, List[Tuple[float, int]]]:
        """Get a snapshot of the order book"""
        bids = []
        asks = []
        
        # Get top bids
        for i, (price, level) in enumerate(self.bids.items()):
            if i >= depth:
                break
            bids.append((price, level.quantity))
        
        # Get top asks
        for i, (price, level) in enumerate(self.asks.items()):
            if i >= depth:
                break
            asks.append((price, level.quantity))
        
        return {
            "bids": bids,
            "asks": asks,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask
        }


@dataclass
class Trade:
    """Represents a trade execution"""
    trade_id: str
    symbol: str
    price: float
    quantity: int
    buyer_id: str
    seller_id: str
    timestamp: int


@dataclass
class MarketData:
    """Represents various market data points"""
    symbol: str
    timestamp: int
    best_bid: float
    best_ask: float
    volume: int = 0
    vwap: float = 0.0