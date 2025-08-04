from typing import Dict, List, Tuple, Optional
from core.agent import Agent
from core.message import Message
from utils.logger import setup_logger
import logging
import time


class OrderBookDepthChecker:
    """Utility class for agents to check order book depth before placing orders"""
    
    def __init__(self, agent: Agent, symbol: str):
        self.agent = agent
        self.symbol = symbol
        self.logger = setup_logger(f"OrderBookDepthChecker.{agent.agent_id}")
        self.pending_queries = {}  # query_id -> callback function
        self.query_timeout = 1000  # milliseconds
        
        # Subscribe to market depth responses
        agent.subscribe(f"{symbol}.MARKET_DEPTH_RESPONSE")
    
    def get_market_depth(self, side: str, depth: int = 5, callback=None) -> Optional[List[Tuple[float, int]]]:
        """
        Get market depth for a specific side up to a certain depth
        If callback is provided, returns None and calls callback with result
        If callback is None, blocks and returns the result directly
        """
        query_id = f"{self.agent.agent_id}_depth_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("get_market_depth", {
                "side": side,
                "depth": depth
            }, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("get_market_depth", {
                "side": side,
                "depth": depth
            })
    
    def get_total_quantity_at_side(self, side: str, depth: int = None, callback=None) -> Optional[int]:
        """
        Get total quantity available at a specific side
        If depth is None, checks all levels
        """
        query_id = f"{self.agent.agent_id}_quantity_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("get_total_quantity_at_side", {
                "side": side,
                "depth": depth
            }, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("get_total_quantity_at_side", {
                "side": side,
                "depth": depth
            })
    
    def get_average_price_for_quantity(self, side: str, quantity: int, callback=None) -> Optional[Tuple[float, float, float]]:
        """
        Calculate the average price, slippage, and fill percentage for a given quantity
        Returns: (average_price, slippage_bps, fill_percentage)
        """
        query_id = f"{self.agent.agent_id}_price_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("get_average_price_for_quantity", {
                "side": side,
                "quantity": quantity
            }, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("get_average_price_for_quantity", {
                "side": side,
                "quantity": quantity
            })
    
    def can_fill_order(self, side: str, quantity: int, min_fill_percent: float = 1.0, callback=None) -> Optional[Tuple[bool, float]]:
        """
        Check if an order can be filled with at least min_fill_percent
        Returns: (can_fill, actual_fill_percentage)
        """
        query_id = f"{self.agent.agent_id}_fill_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("can_fill_order", {
                "side": side,
                "quantity": quantity,
                "min_fill_percent": min_fill_percent
            }, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("can_fill_order", {
                "side": side,
                "quantity": quantity,
                "min_fill_percent": min_fill_percent
            })
    
    def get_liquidity_score(self, reference_quantity: int = 100, callback=None) -> Optional[float]:
        """
        Calculate a liquidity score based on order book depth
        Returns a score between 0 (no liquidity) and 1 (high liquidity)
        """
        query_id = f"{self.agent.agent_id}_liquidity_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("get_liquidity_score", {
                "reference_quantity": reference_quantity
            }, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("get_liquidity_score", {
                "reference_quantity": reference_quantity
            })
    
    def get_spread(self, callback=None) -> Optional[float]:
        """Get the current bid-ask spread"""
        query_id = f"{self.agent.agent_id}_spread_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("get_spread", {}, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("get_spread", {})
    
    def get_imbalance(self, callback=None) -> Optional[float]:
        """
        Calculate order book imbalance
        Positive values indicate more buy pressure
        Negative values indicate more sell pressure
        """
        query_id = f"{self.agent.agent_id}_imbalance_{int(time.time() * 1000)}"
        
        if callback:
            # Asynchronous mode
            self.pending_queries[query_id] = callback
            self._send_query("get_imbalance", {}, query_id)
            return None
        else:
            # Synchronous mode
            return self._send_sync_query("get_imbalance", {})
    
    def handle_market_depth_response(self, message: Message):
        """Handle incoming market depth response messages"""
        payload = message.payload
        query_id = payload.get("query_id")
        
        if query_id in self.pending_queries:
            callback = self.pending_queries.pop(query_id)
            try:
                callback(payload)
            except Exception as e:
                self.logger.error(f"Error in market depth callback: {e}")
    
    def _send_query(self, query_type: str, params: Dict, query_id: str):
        """Send a market depth query to the exchange"""
        payload = {
            "symbol": self.symbol,
            "query_type": query_type,
            "query_id": query_id,
            **params
        }
        self.agent.send_message(f"{self.symbol}.MARKET_DEPTH", payload)
    
    def _send_sync_query(self, query_type: str, params: Dict):
        """Send a synchronous query and wait for response"""
        # In a real implementation, this would need to be handled with proper
        # synchronization primitives. For now, we'll return None to indicate
        # that synchronous queries aren't fully supported in this architecture.
        self.logger.warning("Synchronous queries not fully supported in this architecture")
        return None

