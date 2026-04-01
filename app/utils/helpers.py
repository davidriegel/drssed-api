__all__ = ["helper"]

from ..models.outfit import CanvasPlacement
from flask import has_request_context, g, request
from typing import Any, cast, Sequence
from app.utils.logging import get_logger
from decimal import Decimal

logger = get_logger()

class HelperFunctions:
    @staticmethod
    def ensure_dict(result: Any) -> dict:
        """
        :param result: The object to check
        :return: Result as dictionary
        :raises TypeError: If result is not a dictionary
        """
        if not isinstance(result, dict):
            raise TypeError(f"Expected a dictionary, but got {type(result).__name__}")
        
        return result
    
    @staticmethod
    def build_paginated_response(items, limit, offset, total):
        """
        :param items: The items to send
        :param limit: The limit set for the items
        :param offset: The offset of the query
        :param total: Total amount of items in database
        :return: Dictionary to return
        """
        return {
            "items": items,
            "limit": limit,
            "offset": offset,
            "total": total
        }
    
    def get_request_context(self) -> dict:
        """
        :return: Context dictionary of request
        """
        if not has_request_context():
            return {}
        
        context = {
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'ip': request.remote_addr
        }
        
        if hasattr(g, 'user_id'):
            context['user_id'] = g.user_id
        
        return context
    
    def _parse_canvas_row(self, row: Sequence) -> CanvasPlacement:
        clothing_id, x, y, z, scale, rotation = row
        return CanvasPlacement(
            clothing_id=cast(str, clothing_id),
            x=float(cast(Decimal, x)),
            y=float(cast(Decimal, y)),
            z=int(cast(Decimal, z)),
            scale=float(cast(Decimal, scale)),
            rotation=float(cast(Decimal, rotation))
        )

helper = HelperFunctions()