# 🌐 Colab API Setup - Existing Infrastructure Integration

## 📋 Overview

This setup allows you to use the fine-tuned Qwen 2.5 14B model with RAG V3 through your existing web application, exactly like you did with previous models.

**Architecture:**
```
Web App (Local)
  → api_client.py
    → COLAB_API_URL (ngrok tunnel)
      → Colab (L4 GPU)
        → Fine-tuned Model + RAG V3
          → Response
```

---

## 🚀 Quick Setup (5 minutes)

### Step 1: Get Ngrok Auth Token

1. Go to: https://dashboard.ngrok.com/signup
2. Sign up (free)
3. Go to: https://dashboard.ngrok.com/get-started/your-authtoken
4. Copy your auth token

### Step 2: Add API Cells to Colab Notebook

Open `Qwen_LGS_Production_RAG.ipynb` and add the cells from `COLAB_API_SERVER_CELLS.py`:

1. Install Flask & Ngrok
2. API Server Code
3. Start Ngrok Tunnel (paste your token!)
4. Start Flask Server
5. Test API

**Total time:** 2-3 minutes

### Step 3: Get Your Public URL

After running the cells, you'll see:

```
🌐 PUBLIC API URL: https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app
```

Copy this URL!

### Step 4: Update Local .env

Add to your `.env` file:

```bash
COLAB_API_URL=https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app
```

### Step 5: Test Connection

```bash
python src/test_api_colab.py
```

You should see:
```
✅ Başarılı! Cevap:
{'result': '{...}', 'parsed': {...}, 'success': True}
```

---

## 💻 Use with Existing Web App

**NO CODE CHANGES NEEDED!** 🎉

Your existing `web_app.py` already supports `COLAB_API_URL`:

```python
# web_app.py already has this:
COLAB_API_URL = os.getenv("COLAB_API_URL", "")

# Automatically uses Colab API first:
api_configured = bool(COLAB_API_URL or GEMINI_API_KEY or GROQ_API_KEY)
```

Just run:
```bash
python src/web_app.py
```

Open: http://localhost:5000

It will automatically use your Colab API! ✅

---

## 📊 API Endpoints

### 1. Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model": "Qwen 2.5 14B V13",
  "rag": "V3",
  "gpu": "L4"
}
```

### 2. Generate Question
```bash
POST /generate
Content-Type: application/json

{
  "konu": "Paragraf",
  "alt_konu": "Ana Düşünce"
}
```

Response:
```json
{
  "result": "{\"metin\": \"...\", \"soru\": \"...\", ...}",
  "parsed": {...},
  "success": true
}
```

### 3. Batch Generate
```bash
POST /batch_generate
Content-Type: application/json

{
  "requests": [
    {"konu": "Paragraf", "alt_konu": "Ana Düşünce"},
    {"konu": "Cümlede Anlam", "alt_konu": "Sebep-Sonuç"}
  ]
}
```

---

## 🔧 How It Works

### Colab Side:
1. Model + RAG loaded (from Sections 1-6)
2. Flask server on port 5000
3. Ngrok tunnel → public URL
4. Accepts HTTP requests
5. Generates with RAG V3
6. Returns JSON

### Local Side:
1. `api_client.py` sends request to `COLAB_API_URL`
2. Request goes through ngrok tunnel
3. Colab processes with fine-tuned model + RAG
4. Response comes back
5. Web app displays question

**Exactly like before!** Just with your own model now! 🎯

---

## 💰 Cost Estimate

**L4 GPU:** ~$0.50/hour

**Example Usage:**
- 2 hours/day development: ~$1/day
- 10 hours/week testing: ~$2.50/week
- **Much cheaper than A100!** 💵

**Tip:** Close Colab tab when not using to stop billing

---

## ⚠️ Important Notes

### Ngrok Free Tier Limits:
- ✅ Unlimited requests
- ✅ 1 tunnel at a time
- ✅ HTTPS support
- ⚠️ URL changes on restart
- ⚠️ Some rate limits

**Solution:** If you restart Colab:
1. New URL will be generated
2. Update `.env` with new URL
3. Restart local web app

### Colab Runtime:
- **Max runtime:** 12 hours (then auto-disconnect)
- **Idle timeout:** 90 minutes (but server keeps alive)
- **Solution:** Add keep-alive cell (included in code)

---

## 🎯 Testing Checklist

- [ ] Ngrok token added
- [ ] API cells added to notebook
- [ ] Server started successfully
- [ ] Public URL obtained
- [ ] `.env` updated with URL
- [ ] `test_api_colab.py` passed
- [ ] Web app running
- [ ] Question generated in UI
- [ ] Response shows "colab" as API source

---

## 🐛 Troubleshooting

### "Connection refused"
- Check Colab tab is open
- Check Flask server cell is running
- Check ngrok tunnel is active

### "Timeout"
- L4 GPU selected?
- Model loaded successfully?
- Try increasing timeout in api_client.py

### "404 Not Found"
- Check URL has `/generate` endpoint
- Example: `https://xxx.ngrok-free.app/generate`

### "New URL on restart"
**This is normal!** Ngrok free tier gives new URL each time.

**Workaround:**
1. Paid ngrok → static domain
2. Or: just update .env when restarting

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| **Load Time** | 3-5 minutes (first time) |
| **Generation** | 10-15 seconds |
| **Concurrent Users** | 1 (L4 single GPU) |
| **Uptime** | Up to 12 hours |

**For production with multiple users:**
- Use Cloud Run (see other guide)
- Or: multiple Colab instances

---

## 🎉 Success!

Once setup is complete:

1. ✅ Fine-tuned model running in Colab
2. ✅ RAG V3 integrated
3. ✅ Public API via ngrok
4. ✅ Local web app connected
5. ✅ Existing code working!

**No code changes, just configuration!** 🚀

---

## 📞 Next Steps

**For continuous production use:**
- Consider Cloud Run deployment (more stable)
- Or: Keep Colab as dev environment
- Or: Use both (Colab for testing, Cloud for production)

**For now:**
- Run Colab when developing
- L4 is cost-effective
- Can be your production API!

---

**Version:** V13 Production API  
**Integration:** Existing infrastructure  
**Cost:** ~$0.50/hour (only when running)  
**Setup Time:** 5 minutes
