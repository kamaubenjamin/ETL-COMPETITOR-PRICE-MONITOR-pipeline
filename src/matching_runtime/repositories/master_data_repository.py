from __future__ import annotations

from typing import Dict, List, Optional


class InMemoryMasterDataRepository:
    def __init__(self) -> None:
        self._data: Dict[str, List[Dict[str, str]]] = {
            "customer": [
                {"id": "cust-001", "name": "Acme Corporation", "address": "123 Main St", "email": "billing@acme.com"},
                {"id": "cust-002", "name": "Retail Limited", "address": "400 Market Ave", "email": "orders@retail.com"},
            ],
            "supplier": [
                {"id": "sup-001", "name": "Global Supplies", "vendor_code": "GLOB123", "phone": "555-0100"},
                {"id": "sup-002", "name": "Quickmart Goods", "vendor_code": "QM456", "phone": "555-0200"},
            ],
            "line_item": [
                {"id": "prod-001", "name": "Widget A", "brand": "Acme", "category": "widgets", "size": "small"},
                {"id": "prod-002", "name": "Widget B - Large", "brand": "Acme", "category": "widgets", "size": "large"},
            ],
            "address": [
                {"id": "addr-001", "name": "123 Main St", "address": "123 Main St", "postal_code": "12345"},
                {"id": "addr-002", "name": "400 Market Ave", "address": "400 Market Ave", "postal_code": "67890"},
            ],
        }

    def list_candidates(self, master_data_type: str) -> List[Dict[str, str]]:
        return self._data.get(master_data_type, [])

    def find_candidate(self, master_data_type: str, candidate_id: str) -> Optional[Dict[str, str]]:
        for record in self.list_candidates(master_data_type):
            if record.get("id") == candidate_id:
                return record
        return None
