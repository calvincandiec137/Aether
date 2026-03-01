#!/usr/bin/env python3
"""
Simple FastAPI server for Project AETHER
Single endpoint with dynamic LLM count and optional web search.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import logging
import asyncio
from datetime import datetime

import config
from clean_logging import setup_logging
from evidence_collector import collect_all_evidence
from debate_engine import run_debate
from peer_review import anonymize_transcript, collect_peer_reviews
from judge import judge_synthesis

# Setup logging
logger, _ = setup_logging("aether_simple")

app = FastAPI(title="Aether Simple API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    content: str
    use_web_search: bool = False
    llm_count: int = 5  # 3 or 5

class AnalysisResponse(BaseModel):
    verdict: str
    debate_transcript: str
    peer_reviews: dict
    sources: List[str]
    metadata: dict

@app.post("/process")
async def process_content(request: AnalysisRequest):
    """
    Process content with dynamic agent count.
    """
    # Ensure outputs directory
    import os
    os.makedirs("outputs", exist_ok=True)
    
    if request.llm_count not in [3, 5]:
        # Fallback to nearest or error? User asked for choice.
        # Let's default to 5 if invalid, or error. 
        if request.llm_count < 4:
            request.llm_count = 3
        else:
            request.llm_count = 5
            
    logger.info(f"🚀 Starting analysis with {request.llm_count} LLMs. Search: {request.use_web_search}")
    
    start_time = datetime.now()
    
    try:
        # 1. Evidence Collection
        evidence = {"pro": [], "con": []}
        sources = []
        if request.use_web_search:
            # We treat the content as the factor/topic for simplicity or extract it?
            # User said "content". Let's use content as the topic.
            # Truncate for search query if too long
            topic = request.content[:200].replace("\n", " ")
            logger.info("🔍 Collecting evidence...")
            evidence = collect_all_evidence(topic, enable_scraping=True)
            
            # Extract sources
            for e in evidence.get("pro", []) + evidence.get("con", []):
                if e.get("source") and e["source"] not in sources:
                    sources.append(e["source"])
                    
        # 2. Debate
        logger.info(f"⚔️ Running debate ({request.llm_count} agents)...")
        # Treat content as both report and factor for simplicity in this mode
        debate_transcript = run_debate(report=request.content, factor=request.content[:100]+"...", evidence=evidence, agent_count=request.llm_count)
        
        # 3. Anonymize
        anonymized = anonymize_transcript(debate_transcript)
        
        # 4. Peer Review
        logger.info("👥 Collecting peer reviews...")
        reviews = collect_peer_reviews(anonymized, agent_count=request.llm_count)
        
        # 5. Judge Synthesis
        logger.info("⚖️ Judge synthesizing...")
        verdict = judge_synthesis(factor=request.content[:100]+"...", debate_transcript=debate_transcript, peer_reviews=reviews)
        
        # Save transcript to file (as requested)
        output_filename = f"outputs/debate_{int(start_time.timestamp())}.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(debate_transcript)
        logger.info(f"💾 Transcript saved to {output_filename}")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "verdict": verdict,
            "debate_transcript": debate_transcript,
            "peer_reviews": reviews,
            "sources": sources,
            "metadata": {
                "duration_seconds": duration,
                "llm_count": request.llm_count,
                "model": config.PRO_MODEL_1,
                "transcript_file": output_filename
            }
        }

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
