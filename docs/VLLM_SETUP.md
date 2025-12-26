# vLLM & DeepSeek-OCR Setup Guide

This guide covers setting up vLLM with DeepSeek-OCR for the iFin Bank Verification System.

## Prerequisites

- Python 3.10+
- CUDA 11.8+ (for GPU inference)
- 40GB+ GPU memory (A100 recommended)
- 50GB+ disk space for model weights

## 1. vLLM Installation

### Option A: Quick Install (Nightly Build - Recommended)
```bash
# Create virtual environment
python -m venv vllm-env
source vllm-env/bin/activate  # Linux/Mac
# or vllm-env\Scripts\activate  # Windows

# Install from nightly (includes DeepSeek-OCR support)
pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly
```

### Option B: From Release WHL
```bash
# Download vLLM 0.8.5 WHL from:
# https://github.com/vllm-project/vllm/releases/tag/v0.8.5

pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
pip install flash-attn==2.7.3 --no-build-isolation
```

### Option C: From Source
```bash
git clone https://github.com/vllm-project/vllm.git
cd vllm
pip install -e .
```

## 2. DeepSeek-OCR Model Setup

### Download Model
The model will be downloaded automatically from HuggingFace on first use:
- Model: `deepseek-ai/DeepSeek-OCR`
- Size: ~7GB
- HuggingFace: https://huggingface.co/deepseek-ai/DeepSeek-OCR

### Manual Download (Optional)
```bash
# Using huggingface-cli
pip install huggingface_hub
huggingface-cli download deepseek-ai/DeepSeek-OCR --local-dir ./models/DeepSeek-OCR
```

## 3. Start vLLM Server

### Basic Server Start
```bash
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-OCR \
    --trust-remote-code \
    --max-model-len 8192 \
    --port 8000
```

### With Custom Configuration
```bash
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-OCR \
    --trust-remote-code \
    --max-model-len 8192 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.90 \
    --port 8000 \
    --host 0.0.0.0
```

### Environment Variables (Alternative)
```bash
export VLLM_MODEL_NAME=deepseek-ai/DeepSeek-OCR
export VLLM_MAX_MODEL_LEN=8192
export VLLM_PORT=8000
python -m vllm.entrypoints.openai.api_server
```

## 4. Verify Installation

### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### List Models
```bash
curl http://localhost:8000/v1/models
```

### Test OCR
```python
from vllm import LLM, SamplingParams
from vllm.model_executor.models.deepseek_ocr import NGramPerReqLogitsProcessor
from PIL import Image

# Create model instance
llm = LLM(
    model="deepseek-ai/DeepSeek-OCR",
    enable_prefix_caching=False,
    mm_processor_cache_gb=0,
    logits_processors=[NGramPerReqLogitsProcessor]
)

# Test with image
image = Image.open("test_document.jpg").convert("RGB")
prompt = "<image>\n<|grounding|>Convert the document to markdown."

model_input = [{
    "prompt": prompt,
    "multi_modal_data": {"image": image}
}]

sampling_param = SamplingParams(
    temperature=0.0,
    max_tokens=8192,
)

outputs = llm.generate(model_input, sampling_param)
print(outputs[0].outputs[0].text)
```

## 5. ChromaDB Setup

### Install ChromaDB
```bash
pip install chromadb sentence-transformers
```

### Start ChromaDB Server (Optional)
For production, run ChromaDB as a service:
```bash
chroma run --path ./chromadb_data --port 8001
```

### Initialize Policy Embeddings
```bash
# From Django project directory
python manage.py seed_policies
python manage.py sync_policies
```

## 6. Environment Configuration

Create a `.env` file in the project root:
```env
# vLLM Configuration
VLLM_API_URL=http://localhost:8000
VLLM_MODEL_NAME=deepseek-ai/DeepSeek-OCR
VLLM_TIMEOUT=120
VLLM_MAX_TOKENS=8192

# ChromaDB Configuration
CHROMADB_HOST=localhost
CHROMADB_PORT=8001
CHROMADB_COLLECTION=ifinbank_policies

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Feature Flags
USE_VLLM_OCR=true
USE_CHROMADB=true

# Verification Thresholds
VERIFICATION_AUTO_APPROVE=85.0
VERIFICATION_REVIEW=70.0
VERIFICATION_AUTO_REJECT=50.0
```

## 7. Troubleshooting

### CUDA Out of Memory
- Reduce `--gpu-memory-utilization` to 0.7
- Use smaller image sizes (640x640 instead of 1024x1024)
- Enable tensor parallelism across multiple GPUs

### Slow Inference
- Ensure you're using flash-attn
- Use batch processing for multiple documents
- Consider using smaller model sizes (512x512)

### Connection Refused
- Verify vLLM server is running: `curl http://localhost:8000/health`
- Check firewall settings
- Ensure correct port in VLLM_API_URL

### Model Download Issues
- Check HuggingFace access tokens
- Use VPN if region-restricted
- Download manually and specify local path

## 8. Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    ports:
      - "8000:8000"
    volumes:
      - ./models:/models
    environment:
      - HF_HOME=/models
    command: >
      --model deepseek-ai/DeepSeek-OCR
      --trust-remote-code
      --max-model-len 8192

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - ./chromadb_data:/chroma/chroma
```

### Systemd Service (Linux)
```ini
[Unit]
Description=vLLM DeepSeek-OCR Server
After=network.target

[Service]
Type=simple
User=vllm
WorkingDirectory=/opt/vllm
ExecStart=/opt/vllm/venv/bin/python -m vllm.entrypoints.openai.api_server --model deepseek-ai/DeepSeek-OCR --trust-remote-code --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## References

- vLLM Documentation: https://docs.vllm.ai/
- DeepSeek-OCR GitHub: https://github.com/deepseek-ai/DeepSeek-OCR
- DeepSeek-OCR Paper: https://arxiv.org/abs/2510.18234
- ChromaDB Documentation: https://www.trychroma.com/
- HuggingFace Model: https://huggingface.co/deepseek-ai/DeepSeek-OCR
