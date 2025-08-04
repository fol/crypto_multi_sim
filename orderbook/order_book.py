from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from sortedcontainers import SortedDict
import heapq
from utils.logger import setup_logger


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
        self.logger = setup_logger(f"OrderBook.{symbol}")
    
    def add_limit_order(self, order: Order, execute_partial_market: bool = False,
                       min_fill_percent: float = 0.8) -> List[Tuple[str, float, int, str, str]]:
        """Add a limit order to the book and return any trades generated.
        
        Args:
            order: The limit order to add
            execute_partial_market: If True, execute part of the order as market when price overlaps
                                  with existing orderbook levels
            min_fill_percent: Minimum percentage of order that must be fillable for market-like execution
            
        Returns:
            List of trades generated from the order
        """
        self.logger.debug(f"Adding limit order {order.order_id}: {order.side} {order.quantity} @ {order.price}")
        
        trades = []
        
        # If execute_partial_market is enabled, check if we can execute part of the order as market
        if execute_partial_market:
            # Check if there's liquidity at the exact price level
            liquidity_at_price = 0
            if order.side == "BUY":
                # For buy orders, check asks at the same price
                if order.price in self.asks:
                    liquidity_at_price = self.asks[order.price].quantity
            else:  # SELL
                # For sell orders, check bids at the same price
                if order.price in self.bids:
                    liquidity_at_price = self.bids[order.price].quantity
            
            # If there's liquidity at this price level, execute part of the order as market
            if liquidity_at_price > 0:
                # Create a temporary order with the quantity that can be filled at this price
                fillable_quantity = min(order.quantity, liquidity_at_price)
                market_like_order = Order(
                    order_id=f"{order.order_id}_MARKET_PART",
                    agent_id=order.agent_id,
                    symbol=order.symbol,
                    side=order.side,
                    price=order.price,  # This will be ignored for matching but used for price reference
                    quantity=fillable_quantity,
                    timestamp=order.timestamp
                )
                
                # Execute this portion as a market-like order
                market_trades = self._match_order(market_like_order)
                trades.extend(market_trades)
                
                # Update the original order quantity
                order.quantity -= fillable_quantity
                
                self.logger.debug(f"Executed {fillable_quantity} units of limit order {order.order_id} as market-like trade")
        
        # If there's still quantity left, add it as a regular limit order
        if order.quantity > 0:
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
            
            # Try to match the remaining order
            remaining_trades = self._match_order(order)
            trades.extend(remaining_trades)
            
        if trades:
            self.logger.debug(f"Generated {len(trades)} trades for limit order {order.order_id}")
        return trades
    
    def add_market_order(self, order: Order, min_fill_percent: float = 1.0) -> Tuple[bool, List[Tuple[str, float, int, str, str]]]:
        """Add a market order to the book after checking liquidity and return (can_fill, trades)"""
        self.logger.debug(f"Adding market order {order.order_id}: {order.side} {order.quantity}")
        
        # Check if we can fill the order with sufficient liquidity
        can_fill, actual_fill_percent = self.can_fill_order(order.side, order.quantity, min_fill_percent)
        
        if not can_fill:
            self.logger.debug(f"Market order {order.order_id} rejected due to insufficient liquidity "
                               f"(fill percent: {actual_fill_percent:.2%}, min required: {min_fill_percent:.2%})")
            return False, []
        
        # Store order for later lookup
        self.order_map[order.order_id] = order
        
        # Try to match the order
        trades = self._match_order(order)
        if trades:
            self.logger.debug(f"Generated {len(trades)} trades for market order")
        return True, trades
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID"""
        if order_id not in self.order_map:
            self.logger.debug(f"Order {order_id} not found for cancellation")
            return False
        
        order = self.order_map[order_id]
        self.logger.debug(f"Cancelling order {order_id}: {order.side} {order.quantity} @ {order.price}")
        
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
            # For market orders, match against all available liquidity
            # For limit orders, match only up to the specified price
            price_condition = lambda ask_price: True if order.price == float('inf') else ask_price <= order.price
            while (order.quantity > 0 and self.asks and
                   price_condition(self.asks.peekitem(0)[0])):
                ask_price, ask_level = self.asks.peekitem(0)
                trades.extend(self._execute_match(order, ask_level))
                if ask_level.quantity <= 0:
                    del self.asks[ask_price]
        else:  # SELL
            # Match against bids (highest prices first)
            # For market orders, match against all available liquidity
            # For limit orders, match only up to the specified price
            price_condition = lambda bid_price: True if order.price == 0.0 else bid_price >= order.price
            while (order.quantity > 0 and self.bids and
                   price_condition(self.bids.peekitem(0)[0])):
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
    
    def get_market_depth(self, side: str, depth: int = 5) -> List[Tuple[float, int]]:
        """
        Get market depth for a specific side up to a certain depth
        Returns list of (price, quantity) tuples
        """
        levels = []
        
        if side == "BUY":
            # For buy orders, get asks (what we can buy at)
            for i, (price, level) in enumerate(self.asks.items()):
                if i >= depth:
                    break
                levels.append((price, level.quantity))
        else:  # SELL
            # For sell orders, get bids (what we can sell at)
            for i, (price, level) in enumerate(self.bids.items()):
                if i >= depth:
                    break
                levels.append((price, level.quantity))
        
        return levels
    
    def get_total_quantity_at_side(self, side: str, depth: int = None) -> int:
        """
        Get total quantity available at a specific side
        If depth is None, checks all levels
        """
        total_quantity = 0
        
        if side == "BUY":
            # For buy orders, sum asks
            levels = list(self.asks.items())
            if depth is not None:
                levels = levels[:depth]
            for price, level in levels:
                total_quantity += level.quantity
        else:  # SELL
            # For sell orders, sum bids
            levels = list(self.bids.items())
            if depth is not None:
                levels = levels[:depth]
            for price, level in levels:
                total_quantity += level.quantity
        
        return total_quantity
    
    def get_average_price_for_quantity(self, side: str, quantity: int) -> Tuple[float, float, float]:
        """
        Calculate the average price, slippage, and fill percentage for a given quantity
        Returns: (average_price, slippage_bps, fill_percentage)
        """
        levels = self.get_market_depth(side)
        
        if not levels:
            return 0.0, 0.0, 0.0
        
        total_cost = 0.0
        filled_quantity = 0
        reference_price = levels[0][0]  # Use best price as reference
        
        for price, available_quantity in levels:
            if filled_quantity >= quantity:
                break
            
            quantity_at_level = min(available_quantity, quantity - filled_quantity)
            total_cost += price * quantity_at_level
            filled_quantity += quantity_at_level
        
        if filled_quantity == 0:
            return 0.0, 0.0, 0.0
        
        average_price = total_cost / filled_quantity
        fill_percentage = filled_quantity / quantity
        
        # Calculate slippage in basis points (1/100th of a percent)
        if side == "BUY":
            slippage_bps = ((average_price - reference_price) / reference_price) * 10000
        else:  # SELL
            slippage_bps = ((reference_price - average_price) / reference_price) * 10000
        
        return average_price, slippage_bps, fill_percentage
    
    def can_fill_order(self, side: str, quantity: int, min_fill_percent: float = 1.0) -> Tuple[bool, float]:
        """
        Check if an order can be filled with at least min_fill_percent
        Returns: (can_fill, actual_fill_percentage)
        """
        _, _, fill_percentage = self.get_average_price_for_quantity(side, quantity)
        can_fill = fill_percentage >= min_fill_percent
        return can_fill, fill_percentage
    
    def get_liquidity_score(self, reference_quantity: int = 100) -> float:
        """
        Calculate a liquidity score based on order book depth
        Returns a score between 0 (no liquidity) and 1 (high liquidity)
        """
        bid_quantity = self.get_total_quantity_at_side("SELL")
        ask_quantity = self.get_total_quantity_at_side("BUY")
        
        # Normalize by reference quantity
        bid_score = min(bid_quantity / reference_quantity, 1.0)
        ask_score = min(ask_quantity / reference_quantity, 1.0)
        
        # Return the average of bid and ask scores
        return (bid_score + ask_score) / 2
    
    def get_spread(self) -> float:
        """Get the current bid-ask spread"""
        if self.best_ask == float('inf') or self.best_bid == 0.0:
            return float('inf')
        return self.best_ask - self.best_bid
    
    def get_imbalance(self) -> float:
        """
        Calculate order book imbalance
        Positive values indicate more buy pressure
        Negative values indicate more sell pressure
        """
        bid_quantity = self.get_total_quantity_at_side("SELL")
        ask_quantity = self.get_total_quantity_at_side("BUY")
        
        if bid_quantity + ask_quantity == 0:
            return 0.0
        
        return (bid_quantity - ask_quantity) / (bid_quantity + ask_quantity)


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