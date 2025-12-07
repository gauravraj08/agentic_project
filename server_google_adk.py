import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from fastmcp import FastMCP
from persona.persona_agent import load_prompts
from utils.logger import get_logger

# Initialize Logger
logger = get_logger("SERVER_GOOGLE_8002")

# Load Config
load_dotenv()

# Initialize Server & Models
mcp = FastMCP("Google ADK Tools")
gemini_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
prompts = load_prompts() # Load YAML prompts

@mcp.tool()
def translate_invoice(raw_text: str) -> str:
    """
    Uses Google Gemini to extract JSON from raw invoice text.
    """
    logger.info(f"📨 REQUEST: Translation ({len(raw_text)} chars)")
    
    # 1. Get Prompt from YAML
    sys_prompt = prompts.get("translation_agent", {}).get("system_prompt", "Extract JSON.")
    
    try:
        # 2. Call Gemini
        full_prompt = f"{sys_prompt}\n\n--- INPUT TEXT ---\n{raw_text}"
        response = gemini_model.invoke(full_prompt)
        
        # 3. Clean Output (Remove markdown ```json blocks)
        clean_text = response.content.replace("```json", "").replace("```", "").strip()
        
        # 4. Verify JSON validity
        parsed = json.loads(clean_text) # Should not raise error
        logger.info(f"✅ SUCCESS: Extracted {len(parsed.keys())} fields")
        
        # Return as string (FastMCP handles simple types best)
        return json.dumps(parsed)
        
    except json.JSONDecodeError:
        logger.error("❌ ERROR: Gemini returned invalid JSON")
        return json.dumps({"error": "Invalid JSON from LLM"})
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def generate_report(report_data: str) -> str:
    """
    Uses Google Gemini to write an HTML report based on validation data.
    """
    logger.info(f"📨 REQUEST: Report Generation")
    
    sys_prompt = prompts.get("reporting_agent", {}).get("system_prompt", "Generate HTML.")
    
    try:
        # Call Gemini
        full_prompt = f"{sys_prompt}\n\nDATA: {report_data}"
        response = gemini_model.invoke(full_prompt)
        
        # Clean Output
        html_content = response.content.replace("```html", "").replace("```", "").strip()
        
        logger.info(f"✅ SUCCESS: Generated {len(html_content)} bytes of HTML")
        
        # Wrap in JSON for transport
        return json.dumps({"html": html_content})
        
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        return json.dumps({"html": f"<b>Error Generating Report: {e}</b>"})

if __name__ == "__main__":
    logger.info("🚀 STARTING Google ADK FastMCP Server on Port 8002...")
    mcp.run(transport="sse", port=8002)