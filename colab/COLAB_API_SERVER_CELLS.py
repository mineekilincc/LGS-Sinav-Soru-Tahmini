# Colab API Server Setup - RAG V3 Enhanced
# Add these cells to the end of Qwen_LGS_Production_RAG.ipynb

## ========================================
## NEW CELL: Install Flask & Ngrok
## ========================================

!pip install -q flask pyngrok

print("✅ Flask & Ngrok installed!")


## ========================================
## NEW CELL: API Server Code
## ========================================

from flask import Flask, request, jsonify
from pyngrok import ngrok
import json
import threading

# Create Flask app
app = Flask(__name__)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "model": "Qwen 2.5 14B V13",
        "rag": "V3",
        "gpu": "L4"
    })

# Generate endpoint (matches existing api_client.py structure)
@app.route('/generate', methods=['POST'])
def generate_endpoint():
    """
    Generate question with RAG V3
    
    Expected payload:
    {
        "prompt": {
            "user": "Konu: X\nAlt Konu: Y\n..."
        }
    }
    
    Or simple:
    {
        "konu": "Paragraf",
        "alt_konu": "Ana Düşünce"
    }
    """
    try:
        data = request.json
        
        # Handle both formats
        if "prompt" in data:
            # Format 1: From api_client.py
            user_content = data["prompt"].get("user", "")
            
            # Extract konu/alt_konu from text
            import re
            konu_match = re.search(r'Konu:\s*([^\n]+)', user_content)
            alt_match = re.search(r'Alt Konu:\s*([^\n]+)', user_content)
            
            konu = konu_match.group(1).strip() if konu_match else "Paragraf"
            alt_konu = alt_match.group(1).strip() if alt_match else "Ana Düşünce"
        else:
            # Format 2: Direct
            konu = data.get("konu", "Paragraf")
            alt_konu = data.get("alt_konu", "Ana Düşünce")
        
        # Generate with RAG
        print(f"🎯 Request: {konu} - {alt_konu}")
        result_json = generate_with_rag(
            konu, alt_konu,
            model, tokenizer, rag
        )
        
        # Parse JSON
        result_data = json.loads(result_json)
        
        # Return in expected format
        return jsonify({
            "result": result_json,  # Raw JSON string (for api_client compatibility)
            "parsed": result_data,   # Parsed object
            "success": True
        })
    
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "JSON parse error",
            "message": str(e),
            "success": False
        }), 400
    
    except Exception as e:
        return jsonify({
            "error": "Generation error",
            "message": str(e),
            "success": False
        }), 500

# Batch endpoint (optional, for efficiency)
@app.route('/batch_generate', methods=['POST'])
def batch_generate_endpoint():
    """
    Batch generation
    
    Payload:
    {
        "requests": [
            {"konu": "Paragraf", "alt_konu": "Ana Düşünce"},
            {"konu": "Cümlede Anlam", "alt_konu": "Sebep-Sonuç"}
        ]
    }
    """
    try:
        data = request.json
        requests_list = data.get("requests", [])
        
        results = []
        for req in requests_list:
            konu = req.get("konu", "Paragraf")
            alt_konu = req.get("alt_konu", "Ana Düşünce")
            
            result_json = generate_with_rag(
                konu, alt_konu,
                model, tokenizer, rag
            )
            
            results.append({
                "konu": konu,
                "alt_konu": alt_konu,
                "result": result_json
            })
        
        return jsonify({
            "results": results,
            "count": len(results),
            "success": True
        })
    
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

print("✅ API routes defined!")


## ========================================
## NEW CELL: Start Ngrok Tunnel
## ========================================

# Set ngrok auth token (get from https://dashboard.ngrok.com/get-started/your-authtoken)
NGROK_AUTH_TOKEN = "YOUR_NGROK_TOKEN"  # ⚠️ UPDATE THIS!

# Authenticate ngrok
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# Start tunnel
public_url = ngrok.connect(5000)
print(f"\n{'='*70}")
print(f"🌐 PUBLIC API URL: {public_url}")
print(f"{'='*70}")
print(f"\n📋 Add this to your .env file:")
print(f"COLAB_API_URL={public_url}")
print(f"\n{'='*70}")


## ========================================
## NEW CELL: Start Flask Server
## ========================================

# Run Flask in background thread
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

# Start server
server_thread = threading.Thread(target=run_flask, daemon=True)
server_thread.start()

print("✅ Flask server started!")
print(f"🔗 Local: http://localhost:5000")
print(f"🌐 Public: {public_url}")
print(f"\n📡 Test with:")
print(f"curl -X POST {public_url}/generate \\")
print(f'  -H "Content-Type: application/json" \\')
print(f'  -d \'{{"konu": "Paragraf", "alt_konu": "Ana Düşünce"}}\'')


## ========================================
## NEW CELL: Test API Locally
## ========================================

import requests

# Test health
response = requests.get(f"{public_url}/health")
print("🏥 Health Check:")
print(response.json())

# Test generation
print("\n🎯 Test Generation:")
response = requests.post(
    f"{public_url}/generate",
    json={
        "konu": "Paragraf",
        "alt_konu": "Ana Düşünce"
    },
    timeout=60
)

if response.status_code == 200:
    result = response.json()
    print("✅ Success!")
    print(f"  Words: {len(json.loads(result['result'])['metin'].split())}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)


## ========================================
## USAGE INSTRUCTIONS
## ========================================
"""
🎯 COLAB API SETUP COMPLETE!

**Your Public URL:** {public_url}

**Next Steps:**

1. Copy the public URL above
2. Add to your .env file:
   COLAB_API_URL=https://xxxx.ngrok-free.app

3. Test from local machine:
   python src/test_api_colab.py

4. Use in web app:
   The existing web_app.py will automatically use this API!

**API Endpoints:**

GET  /health
  → Check server status

POST /generate
  → Generate single question
  Body: {"konu": "X", "alt_konu": "Y"}

POST /batch_generate
  → Generate multiple questions
  Body: {"requests": [{...}, {...}]}

**Important:**
- Keep this Colab tab open (server runs here)
- Ngrok tunnel stays active while runtime is alive
- If you restart runtime, you'll get a NEW URL
- Free ngrok tier: some rate limits apply

**Cost:**
- L4 GPU: ~$0.50/hour
- Only pay while running
- Close tab when done to stop billing

**Integration:**
Your existing code (api_client.py, web_app.py) will work
out-of-the-box! Just set COLAB_API_URL in .env
"""


## ========================================
## OPTIONAL: Keep Alive (Prevent Timeout)
## ========================================

# Optional: Add this cell to prevent Colab timeout
# (Prints status every 60 seconds)

import time
from datetime import datetime

def keep_alive():
    while True:
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Server running... (requests: {generator.get_stats()})")
        time.sleep(60)

# Uncomment to enable:
# keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
# keep_alive_thread.start()
