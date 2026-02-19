import os, shutil, time, json, random, replicate, uvicorn
from datetime import date
from pydantic import BaseModel
from typing import Optional, List
from google import genai
from google.genai import types
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from moviepy import VideoFileClip, concatenate_videoclips

# 1. SETUP & AUTH
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Antrolex AI - The Buff-Killer Engine")

# 2. SECURITY & CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    # Uses environment variable or fallback for development
    expected_key = os.getenv("APP_SECRET_KEY", "fallback_dev_key_123")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: Access Denied.")
    return api_key

# 3. DATABASE & CONSTANTS
USER_DB = {} 
MAX_DAILY_ADS = 20
ENERGY_COST_CRATE = 20 

REWARD_CATALOG = {
    "play_10": {"name": "₹10 Google Play Code", "cost": 200}, # The "Easy Grind" hook
    "play_100": {"name": "₹100 Google Play Code", "cost": 1500},
    "play_500": {"name": "₹500 Google Play Code", "cost": 6500}
}

# --- MODELS ---
class UserAction(BaseModel):
    username: str

class RedeemRequest(BaseModel):
    username: str
    reward_type: str

class ScriptRequest(BaseModel):
    topic: str
    game: str = "GTA San Andreas"
    tone: str = "Funny"

# --- UTILITY ---
def get_user_stats(username: str):
    today = str(date.today())
    if username not in USER_DB or USER_DB[username].get("last_date") != today:
        USER_DB[username] = {
            "coins": USER_DB.get(username, {}).get("coins", 0),
            "energy": 100,
            "ads_watched": 0,
            "last_date": today
        }
    return USER_DB[username]

@app.get("/")
def health_check():
    return {"status": "Active", "message": "Antrolex Brain is LIVE & SECURED 🚀"}

# --- FEATURE 1: ECONOMY & ADS ---
@app.post("/watch-rewarded-ad")
async def watch_ad(request: UserAction):
    user = get_user_stats(request.username)
    if user["ads_watched"] >= MAX_DAILY_ADS:
        return {"status": "limit", "message": "Take a break! Daily limit reached."}
    user["ads_watched"] += 1
    user["coins"] += 50 
    return {"status": "success", "new_balance": user["coins"]}

# --- FEATURE 2: MYSTERY CRATE (GACHA) ---
@app.post("/open-crate")
async def open_crate(request: UserAction):
    user = get_user_stats(request.username)
    if user["energy"] < ENERGY_COST_CRATE:
        return {"status": "no_energy", "message": "⚡ Out of Energy!"}
    
    user["energy"] -= ENERGY_COST_CRATE
    # High-stakes probability
    won_coins = random.choices([10, 50, 500, 0], weights=[60, 25, 14, 1], k=1)[0]
    user["coins"] += won_coins
    
    return {
        "status": "success", 
        "won": f"{won_coins} Coins", 
        "new_energy": user["energy"], 
        "new_balance": user["coins"]
    }

# --- FEATURE 3: REWARDS STORE (GOOGLE PLAY) ---
@app.post("/redeem-reward")
async def redeem_reward(request: RedeemRequest, api_key: str = Depends(verify_api_key)):
    user = get_user_stats(request.username)
    if request.reward_type not in REWARD_CATALOG:
        return {"status": "error", "message": "Invalid item."}
        
    reward = REWARD_CATALOG[request.reward_type]
    if user["coins"] < reward["cost"]:
        return {"status": "error", "message": f"Need {reward['cost']} coins."}
        
    user["coins"] -= reward["cost"]
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    play_code = "-".join(["".join(random.choices(chars, k=4)) for _ in range(4)])
    
    return {
        "status": "success", 
        "message": f"Redeemed {reward['name']}!",
        "play_code": play_code,
        "remaining_coins": user["coins"]
    }

# --- FEATURE 4: AI THUMBNAILS ---
@app.post("/generate-viral-thumbnail")
async def generate_viral_thumbnail(user_image: UploadFile = File(...), reference_image: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    try:
        ref_path = f"temp_ref_{reference_image.filename}"
        with open(ref_path, "wb") as buffer: shutil.copyfileobj(reference_image.file, buffer)
        with open(ref_path, "rb") as f: image_bytes = f.read()
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=["Describe style in 3 words.", types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")]
        )
        
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={"prompt": f"YouTube thumbnail, {response.text}, 4k", "aspect_ratio": "16:9"}
        )
        os.remove(ref_path)
        return {"status": "success", "image_url": output[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- FEATURE 5: VIDEO & SCRIPT TOOLS ---
@app.post("/generate-style-transfer-short")
async def generate_style_transfer_short(user_video: UploadFile = File(...), ref_video: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    output_path = f"final_{user_video.filename}"
    return FileResponse(path=output_path, filename=output_path, media_type='video/mp4')

@app.post("/generate-viral-script")
async def generate_script(request: ScriptRequest, api_key: str = Depends(verify_api_key)):
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=f"Viral YouTube script for {request.game} about {request.topic}. Use 'bro'."
        )
        return {"status": "success", "script": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)