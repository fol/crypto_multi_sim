import unittest
from unittest.mock import Mock, patch
from trading_agents import LiquidityProviderAgent
from message import Message
from agent import ActiveAgent


class TestLiquidityProviderAgent(unittest.TestCase):
    """Unit tests for LiquidityProviderAgent"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.agent = LiquidityProviderAgent("LP_TEST", "TEST")
        # Mock the kernel
        self.agent.kernel = Mock()
        self.agent.kernel.get_current_time.return_value = 1000
        # Mock the message broker
        self.agent.message_broker = Mock()
    
    def test_initialization(self):
        """Test that the agent initializes with correct default values"""
        self.assertEqual(self.agent.agent_id, "LP_TEST")
        self.assertEqual(self.agent.symbol, "TEST")
        self.assertEqual(self.agent.initial_fair_value, 100.0)
        self.assertEqual(self.agent.spread, 0.02)
        self.assertEqual(self.agent.limit_order_size, 20)
        self.assertEqual(self.agent.market_order_size, 10)
        self.assertEqual(self.agent.max_orders_per_side, 5)
        self.assertEqual(self.agent.liquidity_provision_interval, 1000)
        self.assertEqual(self.agent.market_trade_interval, 2000)
    
    def test_is_order_book_empty_with_no_state(self):
        """Test that order book is considered empty when no state is available"""
        self.assertTrue(self.agent._is_order_book_empty())
    
    def test_is_order_book_empty_with_empty_book(self):
        """Test that order book is considered empty when it has less than 2 levels on both sides"""
        self.agent.last_order_book_state = {
            "bids": [(99.0, 10)],  # 1 level
            "asks": [(101.0, 15)]  # 1 level
        }
        self.assertTrue(self.agent._is_order_book_empty())
    
    def test_is_order_book_not_empty(self):
        """Test that order book is not considered empty when it has sufficient levels"""
        self.agent.last_order_book_state = {
            "bids": [(99.0, 10), (98.0, 20), (97.0, 30)],  # 3 levels
            "asks": [(101.0, 15), (102.0, 25)]  # 2 levels
        }
        self.assertFalse(self.agent._is_order_book_empty())
    
    def test_cancel_existing_limit_orders(self):
        """Test that existing limit orders are cancelled correctly"""
        # Add some orders to the active orders dict
        self.agent.active_limit_orders = {
            "ORDER1": "BUY",
            "ORDER2": "SELL"
        }
        
        # Call the cancel method
        self.agent._cancel_existing_limit_orders()
        
        # Verify that send_message was called for each order
        self.assertEqual(self.agent.message_broker.publish.call_count, 2)
        
        # Verify that the active orders dict is now empty
        self.assertEqual(len(self.agent.active_limit_orders), 0)
    
    @patch('random.choice')
    def test_make_random_market_trade(self, mock_random_choice):
        """Test that random market trades are placed correctly"""
        # Mock random choice to return "BUY"
        mock_random_choice.return_value = "BUY"
        
        # Set up order book state
        self.agent.last_order_book_state = {
            "best_ask": 101.0,
            "best_bid": 99.0
        }
        
        # Call the method
        self.agent._make_random_market_trade(2000)
        
        # Verify that send_message was called
        self.agent.message_broker.publish.assert_called_once()
        
        # Get the message that was sent
        call_args = self.agent.message_broker.publish.call_args[0]
        message = call_args[0]
        
        # Verify message content
        self.assertEqual(message.topic, "TEST.ORDER")
        self.assertEqual(message.payload["side"], "BUY")
        self.assertEqual(message.payload["price"], float('inf'))  # Market buy order
        self.assertEqual(message.payload["quantity"], 10)  # Default market order size
        self.assertEqual(message.payload["symbol"], "TEST")
    
    def test_receive_message_orderbook(self):
        """Test that order book messages are processed correctly"""
        # Create a message with order book data
        payload = {
            "bids": [(99.0, 10), (98.0, 20)],
            "asks": [(101.0, 15), (102.0, 25)],
            "best_bid": 99.0,
            "best_ask": 101.0
        }
        message = Message(
            timestamp=1000,
            topic="TEST.ORDERBOOK",
            payload=payload,
            source_id="EXCHANGE"
        )
        
        # Process the message
        self.agent.receive_message(message)
        
        # Verify that the last order book state was updated
        self.assertEqual(self.agent.last_order_book_state, payload)
    
    def test_receive_message_price(self):
        """Test that price messages are processed correctly"""
        # Create a message with price data
        payload = {
            "best_bid": 99.0,
            "best_ask": 101.0
        }
        message = Message(
            timestamp=1000,
            topic="TEST.PRICE",
            payload=payload,
            source_id="EXCHANGE"
        )
        
        # Process the message (should not raise an exception)
        self.agent.receive_message(message)
    
    def test_wakeup_scheduling(self):
        """Test that wakeup schedules the next wakeup correctly"""
        # Mock schedule_wakeup
        self.agent.schedule_wakeup = Mock()
        
        # Call wakeup
        self.agent.wakeup(1000)
        
        # Verify that schedule_wakeup was called
        self.agent.schedule_wakeup.assert_called_once()
        
        # Get the scheduled time
        scheduled_time = self.agent.schedule_wakeup.call_args[0][0]
        
        # Verify that the scheduled time is reasonable (should be at least 500ms in the future)
        self.assertGreaterEqual(scheduled_time, 1000)
        self.assertLessEqual(scheduled_time, 3000)  # Should be within a reasonable range


if __name__ == '__main__':
    unittest.main()