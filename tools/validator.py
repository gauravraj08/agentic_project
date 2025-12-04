import requests
from protocols.mcp import BaseTool
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("MOCK_ERP_BASE_URL", "http://127.0.0.1:8000")

class BusinessValidationTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="business_validator",
            description="Validates POs, Vendors, and SKUs against the Enterprise ERP API."
        )
        self.base_url = f"{API_URL}/api/v1"

    def execute(self, validation_type: str, key: str) -> dict:
        """
        Args:
            validation_type: 'po', 'vendor', or 'sku'
            key: The ID to check (e.g., 'PO-1001')
        """
        endpoints = {
            "po": f"/purchase_orders/{key}",
            "vendor": f"/vendors/{key}",
            "sku": f"/skus/{key}"
        }

        if validation_type not in endpoints:
            return {"valid": False, "reason": f"Unknown validation type: {validation_type}"}

        url = f"{self.base_url}{endpoints[validation_type]}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return {"valid": True, "data": response.json(), "message": "Matched in ERP"}
            elif response.status_code == 404:
                return {"valid": False, "reason": f"Not found in ERP: {key}"}
            else:
                return {"valid": False, "reason": f"ERP Error {response.status_code}"}

        except requests.exceptions.ConnectionError:
            return {"valid": False, "reason": "ERP Connection Failed (Is server running?)"}