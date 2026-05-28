import asyncio, logging, os, re
from typing import Literal
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("icon_gen")

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI(title="Icon Generator", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class IconRequest(BaseModel):
    keyword: str = Field(..., description="Icon concept e.g. 'car', 'home'")
    style: Literal["line", "fill"] = Field("line")

class IconResponse(BaseModel):
    svg: str; keyword: str; style: str

def _generate(keyword: str, style: str) -> str:
    stroke = ('stroke="currentColor" fill="none" stroke-width="1.5" '
              'stroke-linecap="round" stroke-linejoin="round"')
    fill_attr = 'fill="currentColor" stroke="none"'
    attrs = stroke if style == "line" else fill_attr

    prompt = f"""You are an expert SVG icon designer. Create a "{keyword}" icon.

DESIGN INSPIRATION (apply these styles):
- PRIMARY (70%): Streamline HQ style — clean geometric shapes, precise proportions,
  symmetric composition, minimal details that maximize recognizability
- SECONDARY (30%): Remix Icon / Lucide / Heroicons — universal, simple, pixel-perfect

RULES:
- ViewBox: 0 0 24 24, drawing area 4-22 (2px padding)  
- Style: {style} ({attrs})
- Draw the LITERAL concept — "car" = car silhouette, never abstract
- Works clearly at 16px, 24px, 32px, 48px
- Use: circle, rect, path, line, ellipse, polyline

Output ONLY the raw SVG element. Start with 

    response = model.generate_content(prompt)
    svg = re.sub(r"```(?:svg|xml)?\n?", "", response.text.strip()).strip()
    svg = re.sub(r"```$", "", svg).strip()
    m = re.search(r", svg)
    svg = m.group(0) if m else svg
    idx = svg.rfind("")
    return svg[:idx+6] if idx != -1 else svg + ""

@app.post("/generate", response_model=IconResponse)
async def generate(req: IconRequest):
    logger.info(ff"icon: {req.keyword} ({req.style})")
    svg = await asyncio.to_thread(_generate, req.keyword, req.style)
    return IconResponse(svg=svg, keyword=req.keyword, style=req.style)

@app.get("/")
async def health(): return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
