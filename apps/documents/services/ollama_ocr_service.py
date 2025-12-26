"""
Ollama OCR Service - CPU-Compatible AI for Document Processing

This service uses Ollama with vision models (like LLaVA) to extract
text from documents when GPU/vLLM is not available.
"""
import base64
import logging
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama service."""
    api_url: str = "http://localhost:11434"
    model: str = "llava"  # Vision model for document understanding
    timeout: int = 120
    max_tokens: int = 4096
    
    @classmethod
    def from_settings(cls) -> 'OllamaConfig':
        return cls(
            api_url=getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434'),
            model=getattr(settings, 'OLLAMA_MODEL', 'llava'),
            timeout=getattr(settings, 'OLLAMA_TIMEOUT', 120),
            max_tokens=getattr(settings, 'OLLAMA_MAX_TOKENS', 4096),
        )


class OllamaOCRService:
    """
    OCR service using Ollama with vision models.
    
    Supports models like:
    - llava: Good for general document understanding
    - llava:13b: Better quality, needs more RAM
    - bakllava: Alternative vision model
    - moondream: Lightweight vision model
    """
    
    EXTRACTION_PROMPT = """Analyze this document image and extract all text content.
    
For identification documents (ID, passport, driver's license), extract:
- Full name
- Date of birth
- ID/Document number
- Issue date
- Expiry date
- Address (if visible)

For bank statements or financial documents, extract:
- Account holder name
- Account number
- Bank name
- Transaction details

For utility bills, extract:
- Customer name
- Account number
- Address
- Bill date
- Amount due

Return the extracted information in a structured format.
If any field is not visible or unclear, indicate "Not visible" or "Unclear".
"""

    def __init__(self, config: OllamaConfig = None):
        self.config = config or OllamaConfig.from_settings()
        self._client = None
        
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.api_url,
                timeout=self.config.timeout,
            )
        return self._client
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = self.client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """List available models in Ollama."""
        try:
            response = self.client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
    
    def has_vision_model(self) -> bool:
        """Check if a vision model is available."""
        models = self.list_models()
        vision_models = ['llava', 'bakllava', 'moondream', 'llava:13b', 'llava:7b']
        return any(vm in model for model in models for vm in vision_models)
    
    def pull_model(self, model: str = None) -> bool:
        """Pull/download a model if not available."""
        model = model or self.config.model
        try:
            logger.info(f"Pulling Ollama model: {model}")
            response = self.client.post(
                "/api/pull",
                json={"name": model},
                timeout=600,  # 10 minutes for download
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def extract_text(
        self,
        image_path: str,
        prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Extract text from document image using Ollama vision model.
        
        Args:
            image_path: Path to the document image
            prompt: Custom extraction prompt (optional)
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Ollama service not available",
                "extracted_text": "",
            }
        
        prompt = prompt or self.EXTRACTION_PROMPT
        
        try:
            # Encode image
            image_base64 = self._encode_image(image_path)
            
            # Call Ollama API
            response = self.client.post(
                "/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "num_predict": self.config.max_tokens,
                    }
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "extracted_text": data.get("response", ""),
                    "model": self.config.model,
                    "total_duration": data.get("total_duration"),
                    "eval_count": data.get("eval_count"),
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "extracted_text": "",
                }
                
        except Exception as e:
            logger.error(f"Ollama extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
            }
    
    def extract_structured_data(
        self,
        image_path: str,
        document_type: str = "id",
    ) -> Dict[str, Any]:
        """
        Extract structured data from document based on type.
        
        Args:
            image_path: Path to document image
            document_type: Type of document (id, passport, bank_statement, utility_bill)
            
        Returns:
            Dictionary with extracted fields
        """
        prompts = {
            "id": """Extract these fields from this ID document image:
                - full_name: Full name as shown
                - date_of_birth: Date of birth (format: YYYY-MM-DD)
                - id_number: ID/Document number
                - gender: Gender if shown
                - issue_date: Issue date
                - expiry_date: Expiry date
                - nationality: Nationality if shown
                
                Return as JSON format. Use null for fields not visible.""",
                
            "passport": """Extract these fields from this passport image:
                - full_name: Full name
                - date_of_birth: Date of birth (YYYY-MM-DD)
                - passport_number: Passport number
                - nationality: Nationality
                - issue_date: Issue date
                - expiry_date: Expiry date
                - place_of_birth: Place of birth
                
                Return as JSON format. Use null for fields not visible.""",
                
            "bank_statement": """Extract these fields from this bank statement:
                - account_holder: Account holder name
                - account_number: Account number
                - bank_name: Bank name
                - statement_date: Statement date
                - opening_balance: Opening balance
                - closing_balance: Closing balance
                
                Return as JSON format. Use null for fields not visible.""",
                
            "utility_bill": """Extract these fields from this utility bill:
                - customer_name: Customer name
                - account_number: Account number
                - service_address: Service address
                - bill_date: Bill date
                - due_date: Due date
                - amount_due: Amount due
                - utility_provider: Utility company name
                
                Return as JSON format. Use null for fields not visible.""",
        }
        
        prompt = prompts.get(document_type, self.EXTRACTION_PROMPT)
        result = self.extract_text(image_path, prompt)
        
        if result["success"]:
            # Try to parse JSON from response
            import json
            try:
                text = result["extracted_text"]
                # Find JSON in response
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = text[start:end]
                    result["structured_data"] = json.loads(json_str)
            except json.JSONDecodeError:
                result["structured_data"] = None
                
        return result


# Singleton instance
_ollama_service = None

def get_ollama_service() -> OllamaOCRService:
    """Get singleton Ollama OCR service instance."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaOCRService()
    return _ollama_service
