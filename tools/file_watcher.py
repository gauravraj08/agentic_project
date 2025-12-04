import os
import shutil
from pathlib import Path
from protocols.mcp import BaseTool

class InvoiceWatcherTool(BaseTool):
    def __init__(self, input_dir="data/incoming", processing_dir="data/processed"):
        super().__init__(name="invoice_watcher", description="Monitors folder for new invoices.")
        self.input_path = Path(input_dir)
        self.process_path = Path(processing_dir)
        
        # Ensure directories exist
        self.input_path.mkdir(parents=True, exist_ok=True)
        self.process_path.mkdir(parents=True, exist_ok=True)

    def execute(self) -> dict:
        """Checks input folder. Moves first found file to processed. Returns path."""
        # Filter for PDF or Images
        valid_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
        files = [f for f in self.input_path.iterdir() if f.suffix.lower() in valid_extensions]
        
        if not files:
            return {"found": False}
        
        target_file = files[0] # Pick the first one
        dest_file = self.process_path / target_file.name
        
        # Move file to prevent double-reading
        shutil.move(str(target_file), str(dest_file))
        
        return {
            "found": True,
            "file_path": str(dest_file),
            "file_name": target_file.name
        }