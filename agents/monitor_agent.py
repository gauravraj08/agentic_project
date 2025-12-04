from tools.file_watcher import InvoiceWatcherTool

def monitor_node(state: dict) -> dict:
    """
    Checks the folder for new files.
    """
    print(" [Workflow] Monitor: Scanning for invoices...")
    watcher = InvoiceWatcherTool()
    result = watcher.execute()
    
    if result["found"]:
        print(f" [Workflow] Monitor: Found {result['file_name']}")
        return {
            "file_path": result["file_path"], 
            "file_name": result["file_name"],
            "status": "PROCESSING"
        }
    else:
        return {"status": "WAITING"}