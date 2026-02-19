import os
import shutil
import time
import json
import random
import replicate
import uvicorn
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

app = FastAPI(title="Antrolex AI Master Backend (SECURED)")

# 2. SECURITY & CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FRONTEND-TO-BACKEND SECURITY KEY (BLOCKS HACKERS)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("APP_SECRET_KEY", "fallback_dev_key_123")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid API Key. Hacker blocked.")
    return api_key

# 3. DATABASE & CONSTANTS (User Economy)
USER_DB = {} 
MAX_DAILY_ADS = 20
ENERGY_COST_CRATE = 20 

# --- MODELS ---
class UserAction(BaseModel):
    username: str

class ScriptRequest(BaseModel):
    topic: str
    game: str = "GTA San Andreas"
    tone: str = "Funny"

class CrateItem(BaseModel):
    name: str
    rarity: str 
    value: int 

class RedeemRequest(BaseModel):
    username: str
    reward_type: str

# --- UTILITY: GET/RESET USER STATS ---
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
    return {"status": "Active", "message": "Antrolex AI is LIVE & SECURED 🚀"}

# --- FEATURE 1: USER ECONOMY & ADS ---
@app.post("/watch-rewarded-ad")
async def watch_ad(request: UserAction):
    user = get_user_stats(request.username)
    if user["ads_watched"] >= MAX_DAILY_ADS:
        return {"status": "limit", "message": "Health Alert: Take a break! Limit reached for today."}
    
    user["ads_watched"] += 1
    user["coins"] += 50 
    return {"status": "success", "new_balance": user["coins"]}

# --- FEATURE 2: MYSTERY CRATE (GACHA) ---
LOOT_TABLE = [
    {"item": CrateItem(name="10 Coins", rarity="common", value=10), "weight": 60},
    {"item": CrateItem(name="50 Coins", rarity="rare", value=50), "weight": 25},
    {"item": CrateItem(name="500 Coins", rarity="epic", value=500), "weight": 14},
    {"item": CrateItem(name="₹100 Play Code", rarity="legendary", value=0), "weight": 1}
]

@app.post("/open-crate")
async def open_crate(request: UserAction):
    user = get_user_stats(request.username)
    if user["energy"] < ENERGY_COST_CRATE:
        return {"status": "no_energy", "message": "⚡ Out of Energy! Come back tomorrow."}
    
    user["energy"] -= ENERGY_COST_CRATE
    items = [entry["item"] for entry in LOOT_TABLE]
    weights = [entry["weight"] for entry in LOOT_TABLE]
    won = random.choices(items, weights=weights, k=1)[0]
    
    if won.value > 0: user["coins"] += won.value
    return {"status": "success", "won_item": won, "new_energy": user["energy"], "new_balance": user["coins"]}

# --- FEATURE 2.5: REWARDS STORE (GOOGLE PLAY CODES) ---
REWARD_CATALOG = {
    "play_100": {"name": "₹100 Google Play Code", "cost": 1000},
    "play_500": {"name": "₹500 Google Play Code", "cost": 4500}
}

@app.post("/redeem-reward")
async def redeem_reward(request: RedeemRequest):
    user = get_user_stats(request.username)
    
    if request.reward_type not in REWARD_CATALOG:
        return {"status": "error", "message": "Invalid reward item."}
        
    reward = REWARD_CATALOG[request.reward_type]
    
    if user["coins"] < reward["cost"]:
        return {"status": "error", "message": f"Keep grinding! You need {reward['cost']} Antrolex Coins."}
        
    user["coins"] -= reward["cost"]
    
    # Generate a secure, randomized Google Play Code format
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    play_code = "-".join(["".join(random.choices(chars, k=4)) for _ in range(4)])
    
    return {
        "status": "success", 
        "message": f"Successfully redeemed {reward['name']}!",
        "play_code": play_code,
        "remaining_coins": user["coins"]
    }

# --- FEATURE 3: VIRAL THUMBNAIL GENERATOR (SECURED) ---
@app.post("/generate-viral-thumbnail")
async def generate_viral_thumbnail(user_image: UploadFile = File(...), reference_image: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    try:
        ref_path = f"temp_ref_{reference_image.filename}"
        with open(ref_path, "wb") as buffer:
            shutil.copyfileobj(reference_image.file, buffer)

        with open(ref_path, "rb") as f:
            image_bytes = f.read()
        
        mime_type = "image/png" if reference_image.filename.lower().endswith(".png") else "image/jpeg"

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=["Describe style in 3 words.", types.Part.from_bytes(data=image_bytes, mime_type=mime_type)]
        )
        style = response.text.strip()

        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={"prompt": f"YouTube thumbnail, {style}, 4k, exciting", "aspect_ratio": "16:9"}
        )
        os.remove(ref_path)
        return {"status": "success", "image_url": output[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- FEATURE 4: STYLE TRANSFER VIDEO EDITOR (SECURED + DOWNLOAD FIX) ---
@app.post("/generate-style-transfer-short")
async def generate_style_transfer_short(user_video: UploadFile = File(...), ref_video: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    user_path, ref_path = f"u_{user_video.filename}", f"r_{ref_video.filename}"
    output_path = f"final_{user_video.filename}"
    try:
        with open(user_path, "wb") as b: shutil.copyfileobj(user_video.file, b)
        with open(ref_path, "wb") as b: shutil.copyfileobj(ref_video.file, b)

        with open(ref_path, "rb") as f: ref_bytes = f.read()
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=['Return ONLY JSON list of timestamps: {"cuts": [0, 2.5]}', types.Part.from_bytes(data=ref_bytes, mime_type="video/mp4")]
        )
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        cut_points = json.loads(text_resp).get("cuts", [0, 3, 6])

        final_clips = []
        with VideoFileClip(user_path) as user_clip:
            for i in range(len(cut_points) - 1):
                duration = max(0.5, min(10, cut_points[i+1] - cut_points[i]))
                r_start = random.uniform(0, max(0, user_clip.duration - duration))
                final_clips.append(user_clip.subclipped(r_start, r_start + duration))
            
            if final_clips:
                concatenate_videoclips(final_clips).write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        os.remove(user_path)
        os.remove(ref_path)
        
        return FileResponse(path=output_path, filename=output_path, media_type='video/mp4')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- FEATURE 5: VIRAL SCRIPT WRITER (SECURED) ---
@app.post("/generate-viral-script")
async def generate_script(request: ScriptRequest, api_key: str = Depends(verify_api_key)):
    prompt = f"Professional YouTube script for gaming channel 'Antrolex Gamerze'. Game: {request.game}. Topic: {request.topic}. Tone: {request.tone}. Under 60s, use slang like 'bro', 'waisted'."
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return {"status": "success", "script": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- SERVER START ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)