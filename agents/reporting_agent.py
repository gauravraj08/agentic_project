import os
import json
import uuid
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
from protocols.a2a import AgentMessage
from persona.persona_agent import load_prompts

# Load Keys
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Define Absolute Path to ensure no confusion
BASE_DIR = Path.cwd()
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class ReportingAgent:
    def __init__(self):
        self.name = "reporting_agent"
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        all_prompts = load_prompts()
        self.agent_config = all_prompts.get("reporting_agent", {})

    def process_message(self, message: AgentMessage) -> AgentMessage:
        print(f"   [Reporter] Processing Request...")
        
        if message.task_type != "GENERATE_REPORT":
            return AgentMessage(self.name, message.sender, "ERROR", {"error": "Invalid Task"}, status="ERROR")

        data = message.payload
        try:
            # 1. Generate Content
            print("   [Reporter] Generating HTML with Gemini...")
            report_html = self._generate_html(data)
            
            print("   [Reporter] Generating Summary...")
            summary = self._generate_summary(data)
            
            # 2. Determine Filename
            inv_num = data.get('invoice_no')
            # Clean filename
            if not inv_num or str(inv_num).lower() in ["none", "null"]:
                safe_id = f"Unknown_{uuid.uuid4().hex[:8]}"
            else:
                safe_id = "".join([c for c in str(inv_num) if c.isalnum() or c in ('-','_')])
            
            # 3. Save Files
            html_path = REPORTS_DIR / f"{safe_id}.html"
            json_path = REPORTS_DIR / f"{safe_id}.json"
            
            print(f"   [Reporter] Saving to: {json_path}")
            
            # Save HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(report_html)
                
            # Save JSON Metadata
            metadata = {
                "invoice_id": safe_id,
                "original_invoice_no": inv_num,
                "status": data.get('validation_status', 'Manual Review'),
                "human_readable_summary": summary,
                "html_report_path": str(html_path),
                "timestamp": datetime.now().isoformat(),
                "audit_trail": {"invoice_data": data}
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print("   [Reporter] Success! Files saved.")

            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_type="REPORT_RESULT",
                payload={"report_html": report_html, "final_report": metadata},
                status="SUCCESS"
            )
        except Exception as e:
            print(f"   [Reporter ERROR] {e}")
            return AgentMessage(self.name, message.sender, "ERROR", {"error": str(e)}, status="ERROR")

    def _generate_html(self, data):
        base_prompt = self.agent_config.get("system_prompt", "Generate HTML report.")
        full_prompt = f"{base_prompt}\nDATA: {data}\nReturn ONLY raw HTML."
        response = self.model.generate_content(full_prompt)
        return response.text.replace("```html", "").replace("```", "").strip()

    def _generate_summary(self, data):
        prompt = f"Summarize this validation in 1 short sentence (Vendor, Total, Reason). Data: {data}"
        response = self.model.generate_content(prompt)
        return response.text.strip()