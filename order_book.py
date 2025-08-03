import heapq
from typing import List, Optional


class OrderBook:
    """Order book management for perpetual contracts."""
    
    def __init__(self):
        self.bids = []  # Max heap (negative prices)
        self.asks = []  # Min heap
        self.trades = []
    
    def add_order(self, order: dict):
        """Add an order to the order book."""
        if order['side'] == 'buy':
            # Max heap for bids (negate price)
            heapq.heappush(self.bids, (-order['price'], order['timestamp'], order))
        else:
            # Min heap for asks
            heapq.heappush(self.asks, (order['price'], order['timestamp'], order))
    
    def match_orders(self) -> List[dict]:
        """Match buy and sell orders based on price-time priority."""
        matches = []
        
        while (self.bids and self.asks and 
               -self.bids[0][0] >= self.asks[0][0]):  # bid >= ask
            
            # Get best bid and ask
            neg_bid_price, bid_time, bid_order = heapq.heappop(self.bids)
            ask_price, ask_time, ask_order = heapq.heappop(self.asks)
            
            # Create trade
            trade = {
                'price': ask_price,  # Use ask price for trade
                'quantity': min(bid_order['quantity'], ask_order['quantity']),
                'timestamp': max(bid_time, ask_time),
                'bid_id': bid_order['id'],
                'ask_id': ask_order['id']
            }
            
            matches.append(trade)
            self.trades.append(trade)
            
            # Handle partial fills
            if bid_order['quantity'] > ask_order['quantity']:
                # Remaining bid
                bid_order['quantity'] -= ask_order['quantity']
                heapq.heappush(self.bids, (neg_bid_price, bid_time, bid_order))
            elif ask_order['quantity'] > bid_order['quantity']:
                # Remaining ask
                ask_order['quantity'] -= bid_order['quantity']
                heapq.heappush(self.asks, (ask_price, ask_time, ask_order))
        
        return matches
    
    def cancel_order(self, order_id: str, side: str) -> bool:
        """Cancel an order from the order book."""
        book = self.bids if side == 'buy' else self.asks
        
        for i, (_, _, order) in enumerate(book):
            if order['id'] == order_id:
                book.pop(i)
                heapq.heapify(book)
                return True
        
        return False
    
    def get_best_bid(self) -> Optional[float]:
        """Get the best bid price."""
        if not self.bids:
            return None
        return -self.bids[0][0]
    
    def get_best_ask(self) -> Optional[float]:
        """Get the best ask price."""
        if not self.asks:
            return None
        return self.asks[0][0]