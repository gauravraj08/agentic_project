from fastapi import FastAPI, HTTPException
import json
import os
from typing import Optional

app = FastAPI(title="Mock ERP System")

# Define paths to your JSON data
DATA_DIR = "data/ERP_mockdata"
VENDORS_FILE = os.path.join(DATA_DIR, "vendors.json")
SKU_FILE = os.path.join(DATA_DIR, "sku_master.json")
PO_FILE = os.path.join(DATA_DIR, "po_records.json")

def load_data(filepath):
    """Helper to load JSON data safely"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.get("/")
def health_check():
    return {"status": "ERP System Online", "version": "1.0"}

@app.get("/api/v1/vendors/{vendor_id}")
def get_vendor(vendor_id: str):
    vendors = load_data(VENDORS_FILE)
    vendor = next((v for v in vendors if v["vendor_id"] == vendor_id), None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

@app.get("/api/v1/purchase_orders/{po_number}")
def get_purchase_order(po_number: str):
    pos = load_data(PO_FILE)
    po = next((p for p in pos if p["po_number"] == po_number), None)
    if not po:
        raise HTTPException(status_code=404, detail="PO Number not found")
    return po

@app.get("/api/v1/skus/{item_code}")
def get_sku_details(item_code: str):
    skus = load_data(SKU_FILE)
    sku = next((s for s in skus if s["item_code"] == item_code), None)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    return sku

# Helper to run locally if executed directly
if __name__ == "__main__":
    import uvicorn
    # Runs on localhost:8000
    uvicorn.run(app, host="127.0.0.1", port=8003)