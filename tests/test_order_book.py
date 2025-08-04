import unittest
from orderbook.order_book import OrderBook, Order


class TestOrderBook(unittest.TestCase):
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

    def test_limit_order_with_partial_market_execution(self):
        """Test that limit orders can execute partially as market when overlapping with orderbook levels"""
        # Add some asks to the order book at price 100.0
        order1 = Order("ASK1", "AGENT1", "TEST", "SELL", 100.0, 50, 1000)
        order2 = Order("ASK2", "AGENT2", "TEST", "SELL", 100.0, 30, 1001)
        self.order_book.add_limit_order(order1)
        self.order_book.add_limit_order(order2)
        
        # Place a limit buy order at the same price (100.0) with execute_partial_market=True
        limit_order = Order("LIMIT1", "AGENT3", "TEST", "BUY", 100.0, 100, 1002)
        trades = self.order_book.add_limit_order(limit_order, execute_partial_market=True)
        
        # Verify that partial execution occurred (should have 2 trades for the 80 units available)
        self.assertEqual(len(trades), 2)
        self.assertEqual(sum(trade[2] for trade in trades), 80)  # Total quantity executed
        
        # Verify that the remaining 20 units are still in the order book as a limit order
        self.assertIn("LIMIT1", self.order_book.order_map)
        self.assertEqual(self.order_book.order_map["LIMIT1"].quantity, 20)

    def test_limit_order_with_no_overlap_no_partial_execution(self):
        """Test that limit orders don't execute partially when there's no overlap and execute_partial_market=True"""
        # Add some asks to the order book at price 101.0
        order1 = Order("ASK1", "AGENT1", "TEST", "SELL", 101.0, 50, 1000)
        self.order_book.add_limit_order(order1)
        
        # Place a limit buy order at a better price (100.0) with execute_partial_market=True
        limit_order = Order("LIMIT1", "AGENT3", "TEST", "BUY", 100.0, 100, 1002)
        trades = self.order_book.add_limit_order(limit_order, execute_partial_market=True)
        
        # Verify that no execution occurred (should have 0 trades)
        self.assertEqual(len(trades), 0)
        
        # Verify that the full order is in the order book as a limit order
        self.assertIn("LIMIT1", self.order_book.order_map)
        self.assertEqual(self.order_book.order_map["LIMIT1"].quantity, 100)


if __name__ == '__main__':
    unittest.main()