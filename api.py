from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Import your existing modules
from ai_engine import process_ai_request  # Adjust to your exact function name in ai_engine.py
from memory import MemoryManager         # Adjust to your database logic in memory.py

app = FastAPI(title="KingZarry AI Mobile API")

# Define request format sent from Expo app
class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.get("/")
def read_root():
    return {"status": "KingZarry AI API is active"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Process message through your existing AI routing (Groq/Gemini/OpenAI)
        # 2. Memory engine stores and updates conversational context
        response_text = await process_ai_request(
            user_id=request.user_id, 
            prompt=request.message
        )
        return {"status": "success", "reply": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
