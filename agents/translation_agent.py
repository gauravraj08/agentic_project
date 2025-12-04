import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from protocols.a2a import AgentMessage
from persona.persona_agent import load_prompts

# Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

class TranslationAgent:
    def __init__(self):
        self.name = "translation_agent"
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Load Prompts from YAML
        all_prompts = load_prompts()
        self.agent_config = all_prompts.get("translation_agent", {})
        
        # Fallback prompt if YAML is empty/missing
        self.default_prompt = """
        You are an expert AI Data Extractor. 
        Extract Invoice No, Date, Vendor, Currency, Total, and Line Items. 
        Translate descriptions to English. 
        Return strictly JSON.
        """

    def process_message(self, message: AgentMessage) -> AgentMessage:
        if message.task_type != "TRANSLATE_EXTRACT":
            return self._create_error_response(message, "Invalid Task Type")

        raw_text = message.payload.get("raw_text", "")
        if not raw_text:
            return self._create_error_response(message, "Empty input text")

        try:
            structured_data = self._call_gemini(raw_text)
            
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_type="TRANSLATION_RESULT",
                payload={"structured_data": structured_data},
                status="SUCCESS"
            )
        except Exception as e:
            return self._create_error_response(message, str(e))

    def _call_gemini(self, text):
        # 1. Get System Prompt from YAML (or use fallback)
        system_prompt = self.agent_config.get("system_prompt", self.default_prompt)
        
        # 2. Construct Full Prompt
        full_prompt = f"""
        {system_prompt}
        
        --- INPUT TEXT START ---
        {text}
        --- INPUT TEXT END ---
        """
        
        # 3. Call Model
        response = self.model.generate_content(full_prompt)
        
        # 4. Clean JSON output
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    def _create_error_response(self, original_msg, error_desc):
        return AgentMessage(
            sender=self.name,
            receiver=original_msg.sender,
            task_type="ERROR",
            payload={"error": error_desc},
            status="ERROR"
        )