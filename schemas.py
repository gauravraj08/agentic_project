from typing import TypedDict, List, Optional, Dict, Any

class InvoiceLineItem(TypedDict):
    description: str
    qty: float
    unit_price: float
    total: float
    po_number: Optional[str]
    item_code: Optional[str] # Added for ERP matching

class ExtractedInvoice(TypedDict):
    invoice_no: str
    invoice_date: str
    vendor_name: str
    currency: str
    total_amount: float
    line_items: List[InvoiceLineItem]
    translation_confidence: float

class InvoiceState(TypedDict):
    """
    The Shared Memory of the Workflow.
    """
    # 1. Input
    file_path: str
    file_name: str
    
    # 2. Extraction & Translation
    raw_text: str
    structured_data: Optional[ExtractedInvoice]
    
    # 3. Validation
    validation_results: Dict[str, Any] # Stores pass/fail for PO, Vendor, etc.
    is_valid: bool
    discrepancies: List[str]
    
    # 4. Output
    final_report_html: str
    status: str # "PROCESSING", "COMPLETED", "FAILED"
    error_message: Optional[str]