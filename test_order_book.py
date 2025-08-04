import unittest
from order_book import OrderBook, Order


class TestOrderBookMarketOrders(unittest.TestCase):
    """Unit tests for OrderBook market order functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.order_book = OrderBook("TEST")
    
    def test_market_order_with_sufficient_liquidity(self):
        """Test placing market order when orderbook has sufficient liquidity"""
        # Add some asks to the order book
        order1 = Order("ASK1", "AGENT1", "TEST", "SELL", 100.0, 50, 1000)
        order2 = Order("ASK2", "AGENT2", "TEST", "SELL", 101.0, 50, 1001)
        self.order_book.add_limit_order(order1)
        self.order_book.add_limit_order(order2)
        
        # Place a market buy order that can be fully filled
        market_order = Order("MARKET1", "AGENT3", "TEST", "BUY", float('inf'), 75, 1002)
        can_fill, trades = self.order_book.add_market_order(market_order, min_fill_percent=0.8)
        
        # Verify the order was accepted
        self.assertTrue(can_fill)
        self.assertEqual(len(trades), 2)  # Should generate 2 trades
    
    def test_market_order_with_insufficient_liquidity(self):
        """Test placing market order when orderbook has insufficient liquidity"""
        # Add some asks to the order book
        order1 = Order("ASK1", "AGENT1", "TEST", "SELL", 100.0, 50, 1000)
        self.order_book.add_limit_order(order1)
        
        # Place a market buy order that cannot be fully filled
        market_order = Order("MARKET1", "AGENT3", "TEST", "BUY", float('inf'), 100, 1002)
        can_fill, trades = self.order_book.add_market_order(market_order, min_fill_percent=0.8)
        
        # Verify the order was rejected
        self.assertFalse(can_fill)
        self.assertEqual(len(trades), 0)  # Should generate no trades
    
    def test_limit_order_no_liquidity_check(self):
        """Test that limit orders don't require liquidity checking"""
        # Place a limit buy order in an empty order book
        limit_order = Order("LIMIT1", "AGENT1", "TEST", "BUY", 95.0, 100, 1000)
        trades = self.order_book.add_limit_order(limit_order)
        
        # Verify the order was accepted (no liquidity check for limit orders)
        self.assertEqual(len(trades), 0)  # No trades yet, but order is accepted
        self.assertIn("LIMIT1", self.order_book.order_map)  # Order should be in the book


if __name__ == '__main__':
    unittest.main()