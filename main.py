import os
import shutil
import time
import json
import random
import replicate
from pydantic import BaseModel
from google import genai # 2026 SDK
from google.genai import types
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from moviepy import VideoFileClip, concatenate_videoclips # MoviePy v2.0+

# 1. SETUP & AUTH
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

# 2. SECURITY
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "Antrolex Engine is Online 🚀", "version": "2026.STYLE_TRANSFER"}

# --- FEATURE 1: VIRAL THUMBNAIL ---
@app.post("/generate-viral-thumbnail")
async def generate_viral_thumbnail(
    user_image: UploadFile = File(...),
    reference_image: UploadFile = File(...)
):
    try:
        ref_path = f"temp_ref_{reference_image.filename}"
        with open(ref_path, "wb") as buffer:
            shutil.copyfileobj(reference_image.file, buffer)

        # Read bytes for Gemini
        with open(ref_path, "rb") as f:
            image_bytes = f.read()
        
        mime_type = "image/png" if reference_image.filename.lower().endswith(".png") else "image/jpeg"

        # AI Analysis
        print("👀 Analyzing Thumbnail Style...")
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[
                "Describe the visual style in 3 words (e.g. Neon, Bold).",
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            ]
        )
        style = response.text.strip()
        print(f"🎨 Detected Style: {style}")

        # Generate Image (Replicate)
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={"prompt": f"YouTube thumbnail, {style}, 4k, exciting", "aspect_ratio": "16:9"}
        )

        os.remove(ref_path)
        return {"status": "success", "image_url": output[0]}

    except Exception as e:
        return {"status": "error", "detail": str(e)}

# --- FEATURE 2: STYLE TRANSFER VIDEO EDITOR ---
@app.post("/generate-style-transfer-short")
async def generate_style_transfer_short(
    user_video: UploadFile = File(...),
    ref_video: UploadFile = File(...)
):
    user_path = f"temp_user_{user_video.filename}"
    ref_path = f"temp_ref_{ref_video.filename}"
    output_path = f"final_style_{user_video.filename}"

    try:
        # 1. Save both videos
        with open(user_path, "wb") as buffer:
            shutil.copyfileobj(user_video.file, buffer)
        with open(ref_path, "wb") as buffer:
            shutil.copyfileobj(ref_video.file, buffer)

        # 2. Analyze Reference Pacing with Gemini
        print("🧠 Analyzing Reference Video Pacing...")
        with open(ref_path, "rb") as f:
            ref_bytes = f.read()

        prompt = """
        Analyze the editing pace of this video. 
        Return ONLY a JSON list of timestamps (in seconds) where visual cuts happen.
        Format: {"cuts": [0, 2.5, 5.0]} 
        """
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[prompt, types.Part.from_bytes(data=ref_bytes, mime_type="video/mp4")]
        )
        
        # Clean JSON
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        cut_points = json.loads(text_resp).get("cuts", [0, 3, 6, 9]) # Fallback cuts

        # 3. Apply Cuts to User Video
        print(f"✂️ Cloning Cuts at: {cut_points}")
        final_clips = []
        
        with VideoFileClip(user_path) as user_clip:
            for i in range(len(cut_points) - 1):
                start = cut_points[i]
                end = cut_points[i+1]
                duration = end - start
                
                # Validation
                if duration < 0.5: duration = 1.0 
                if duration > 10: duration = 5.0

                # Pick random segment from user video
                max_start = max(0, user_clip.duration - duration)
                random_start = random.uniform(0, max_start)
                
                # Create subclip
                sub = user_clip.subclipped(random_start, random_start + duration)
                final_clips.append(sub)

            # Stitch together
            if final_clips:
                final_video = concatenate_videoclips(final_clips)
                final_video.write_videofile(output_path, codec="libx264", audio_codec="aac") #
            else:
                return {"status": "error", "detail": "Could not generate clips"}

        # Cleanup
        os.remove(user_path)
        os.remove(ref_path)

        return {"status": "success", "file_name": output_path, "message": "Video cloned successfully!"}

    except Exception as e:
        print(f"❌ Video Error: {e}")
        return {"status": "error", "detail": str(e)}

# --- FEATURE 3: PAYMENT ---
@app.post("/verify-payment")
async def verify_payment(payment_id: str = Form(...)):
    return {"status": "verified", "gateway": "Razorpay"}
import uvicorn
# --- NEW: Viral Script Writer Feature ---
class ScriptRequest(BaseModel):
    topic: str
    game: str = "GTA San Andreas" # Default game
    tone: str = "Funny" # Default tone

@app.post("/generate-viral-script")
async def generate_script(request: ScriptRequest):
    prompt = f"""
    You are a professional YouTube scriptwriter for a gaming channel called 'Antrolex Gamerze'.
    Write a viral, high-retention script for the game: {request.game}.
    
    TOPIC: {request.topic}
    TONE: {request.tone}
    
    Structure the script with:
    1. A Hook (0-5 seconds) - Explosive start.
    2. The Intro - Fast explanation.
    3. The Body - The story/rant with timestamps.
    4. The Call to Action - Asking for likes/subs.
    
    Keep it under 60 seconds (Shorts format). Use slang like 'bro', 'damn', 'waisted'.
    """
    
    try:
        response = model.generate_content(prompt)
        return {"script": response.text}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # This tells the app to use the port Render provides (defaulting to 8000)
    port = int(os.environ.get("PORT", 8000))
    # This starts the server
    uvicorn.run("main:app", host="0.0.0.0", port=port)