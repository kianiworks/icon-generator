import asyncio, logging, os, re
from textwrap import dedent
from typing import Literal
from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from perplexity import AsyncPerplexity
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("icon_generator")

app = FastAPI(title="Icon Generator", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class IconRequest(BaseModel):
    keyword: str = Field(..., description="Icon concept")
    style: Literal["line", "fill"] = Field("line")

class IconResponse(BaseModel):
    svg: str
    keyword: str
    style: str
    benchmark_summary: str

async def research_streamline(keyword: str) -> str:
    client = AsyncPerplexity()
    r = await client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {"role":"system","content":"Expert icon designer. Describe geometry precisely."},
            {"role":"user","content":f'How is a "{keyword}" icon designed on streamlinehq.com? Describe exact shapes, proportions, visual geometry.'}
        ], max_tokens=400,)
    return r.choices[0].message.content

async def research_others(keyword: str) -> str:
    client = AsyncPerplexity()
    r = await client.chat.completions.create(
        model="sonar",
        messages=[{"role":"user","content":f'How is "{keyword}" icon in Remix Icon, Lucide, Heroicons? (2-3 sentences)'}],
        max_tokens=200,)
    return r.choices[0].message.content

async def generate_svg(keyword: str, style: str, bench: dict) -> str:
    client = AsyncAnthropic()
    sys_p = "You are SVG icon designer (Remix Icon style). Output ONLY raw SVG. ViewBox 0 0 24 24. stroke-width=1.5. stroke-linecap=round. NO abstract metaphors. Draw the literal concept."
    stroke_fill = "stroke" if style == "line" else "fill"
    prompt = (f'Generate "{keyword}" icon, {style} style.\n\nStreamline HQ (7/10 weight):\n{bench["streamline"]}\n\nOther libs (3/10):\n{bench["others"]}\n\nOutput SVG:')
    r = await client.messages.create(model="claude-sonnet-4-5", max_tokens=2000,
        system=sys_p, messages=[{"role":"user","content":prompt}])
    svg = re.sub(r"```(?:svg|xml)?\n?", "", r.content[0].text.strip()).strip()
    m = re.search(r", svg)
    svg = m.group(0) if m else svg
    idx = svg.rfind("")
    return svg[:idx+6] if idx != -1 else svg+""

@app.post("/generate", response_model=IconResponse)
async def generate_icon(req: IconRequest):
    bench = await asyncio.gather(research_streamline(req.keyword), research_others(req.keyword))
    bench = {"streamline": bench[0], "others": bench[1]}
    svg = await generate_svg(req.keyword, req.style, bench)
    return IconResponse(svg=svg, keyword=req.keyword, style=req.style,
        benchmark_summary=f"[Streamline 7/10] {bench['streamline']}\n\n[Others 3/10] {bench['others']}")

@app.get("/")
async def health(): return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))