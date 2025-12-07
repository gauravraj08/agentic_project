import requests
from protocols.mcp import BaseTool

class BusinessValidationTool(BaseTool):
    # --- FIX: Point to Port 8003 (where Mock ERP is now running) ---
    def __init__(self, api_base_url="http://127.0.0.1:8003/api/v1"):
        super().__init__(
            name="business_validator",
            description="Validates POs, Vendors, and SKUs against the ERP API."
        )
        self.base_url = api_base_url

    def execute(self, validation_type: str, key: str) -> dict:
        """
        validation_type: 'po' or 'vendor' or 'sku'
        key: The ID to check (e.g., 'PO-1001')
        """
        # Map simple commands to API endpoints
        endpoints = {
            "po": f"/purchase_orders/{key}",
            "vendor": f"/vendors/{key}",
            "sku": f"/skus/{key}"
        }

        if validation_type not in endpoints:
            return {"valid": False, "reason": f"Unknown validation type: {validation_type}"}

        url = f"{self.base_url}{endpoints[validation_type]}"
        
        try:
            # Call the Mock ERP API
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True, 
                    "data": data, 
                    "message": "Match found in ERP."
                }
            elif response.status_code == 404:
                return {
                    "valid": False, 
                    "reason": f"{validation_type} failed: {key} not found in ERP."
                }
            else:
                return {
                    "valid": False, 
                    "reason": f"ERP Error: {response.status_code}"
                }

        except requests.exceptions.ConnectionError:
            return {
                "valid": False, 
                "reason": f"ERP System Unreachable at {self.base_url}. Is it running on Port 8003?"
            }