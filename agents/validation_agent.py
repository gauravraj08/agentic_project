import json
from tools.validator import BusinessValidationTool
from persona.persona_agent import load_rules

def validation_node(state: dict) -> dict:
    """
    Validates extracted invoice data against Dynamic Business Rules (YAML) 
    and the Mock ERP System.
    """
    print(" [Workflow] Validator: Checking Dynamic Business Rules...")
    
    # 1. Input Validation
    data = state.get("structured_data")
    if not data:
        return {
            "validation_results": {}, 
            "discrepancies": ["No structured data found to validate"], 
            "is_valid": False
        }

    # 2. Load Rules from Config
    config = load_rules()
    rules = config.get("validation_rules", {})
    
    # Extract specific rules with defaults
    mandatory_fields = rules.get("mandatory_fields", ["invoice_no", "total_amount"])
    price_tolerance = rules.get("price_tolerance_percent", 5.0)
    auto_reject_po = rules.get("auto_reject_if_po_missing", True)

    validator = BusinessValidationTool()
    discrepancies = []
    results = {}

    # 3. Rule Check: Mandatory Fields
    print(f"   - Checking {len(mandatory_fields)} mandatory fields...")
    for field in mandatory_fields:
        # Check if field is missing or empty/None/Zero
        value = data.get(field)
        if value is None or value == "":
            discrepancies.append(f"Missing mandatory field: {field}")

    # 4. Rule Check: ERP PO Validation
    po_number = None
    # Attempt to find PO number in line items or header (if schema supported it)
    for item in data.get('line_items', []):
        if item.get('po_number'):
            po_number = item['po_number']
            break
    
    if po_number:
        print(f"   - Validating PO: {po_number}")
        res = validator.execute("po", po_number)
        results["po_check"] = res
        
        if not res["valid"]:
            discrepancies.append(f"Invalid PO Number: {po_number}")
        else:
            # --- Deep Line-Item Verification ---
            erp_data = res["data"]
            # Create a lookup map for ERP items: {SKU: ItemData}
            erp_items = {item["item_code"]: item for item in erp_data.get("line_items", [])}
            
            print(f"   - Verifying Line Items against ERP records...")
            
            for invoice_item in data.get("line_items", []):
                # Try to match by Item Code (SKU)
                sku = invoice_item.get("item_code")
                # If SKU missing, you might check Description, but let's stick to SKU for strictness
                
                matched_erp_item = erp_items.get(sku)
                
                if matched_erp_item:
                    # A. Price Check
                    try:
                        inv_price = float(invoice_item.get("unit_price", 0))
                        erp_price = float(matched_erp_item.get("unit_price", 0))
                        
                        if erp_price > 0:
                            # Calculate percentage difference
                            diff_percent = abs((inv_price - erp_price) / erp_price) * 100
                            
                            if diff_percent > price_tolerance:
                                discrepancies.append(
                                    f"Price Mismatch for {sku}: Inv ${inv_price} vs ERP ${erp_price} "
                                    f"(Diff: {diff_percent:.2f}% > Limit: {price_tolerance}%)"
                                )
                    except (ValueError, TypeError):
                         discrepancies.append(f"Invalid price format for item {sku}")

                    # B. Quantity Check
                    try:
                        inv_qty = float(invoice_item.get("qty", 0))
                        erp_qty = float(matched_erp_item.get("qty", 0))
                        
                        if inv_qty > erp_qty:
                             discrepancies.append(f"Over-billing Quantity for {sku}: Inv {inv_qty} > PO {erp_qty}")
                    except (ValueError, TypeError):
                        pass # Ignore qty check if format is bad
                
                else:
                    # Item exists on Invoice but not on PO
                    if sku:
                        # Only flag if we actually have an SKU to check
                        # pass # or discrepancies.append(f"Item {sku} not found on Purchase Order")
                        pass 

    elif auto_reject_po:
        # If no PO found and rule says "Auto Reject"
        discrepancies.append("Missing PO Number (Auto-Rejection Rule Applied)")
    else:
        print("   - Warning: No PO Number found, but auto-reject is OFF.")

    # 5. Final Decision
    is_valid = len(discrepancies) == 0
    
    if is_valid:
        print("   - Result: APPROVED")
    else:
        print(f"   - Result: REJECTED ({len(discrepancies)} issues)")
    
    return {
        "validation_results": results,
        "discrepancies": discrepancies,
        "is_valid": is_valid
    }