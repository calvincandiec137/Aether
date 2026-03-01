#!/usr/bin/env python3
"""
FastAPI server for Project AETHER - Progressive Analysis API
Provides 3-stage response: factors → per-factor analysis → final synthesis
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List

import config
from clean_logging import setup_logging
from dashboard import log_event, update_progress, complete_task, error_task
from factor_extraction import extract_factors
from evidence_collector import collect_all_evidence
from debate_engine import run_debate
from peer_review import anonymize_transcript, collect_peer_reviews
from judge import judge_synthesis, generate_final_report

# Setup clean logging
logger, _ = setup_logging("aether_api")

app = FastAPI(title="Project AETHER API", version="2.0.0")

# Enable CORS - configured for ngrok and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# In-memory storage
documents: Dict[str, dict] = {}
factor_results: Dict[str, dict] = {}

# ================================================================================
# REQUEST/RESPONSE MODELS
# ================================================================================

class UploadRequest(BaseModel):
    report_text: str
    enable_web_scraping: bool = True

class FactorInfo(BaseModel):
    id: int
    title: str

class UploadResponse(BaseModel):
    status: str
    document_id: str
    factors: List[FactorInfo]
    total_factors: int

class AgentResponse(BaseModel):
    agent_id: str
    response: str

class PeerReviewScore(BaseModel):
    agent_id: str
    score: float

class JudgeVerdict(BaseModel):
    verdict: str
    reasoning: str
    confidence: int

class DebateInfo(BaseModel):
    pro_argument: str
    con_argument: str
    judge_verdict: JudgeVerdict
    peer_review_scores: List[PeerReviewScore]

class FactorAnalysisResponse(BaseModel):
    factor_id: int
    factor_title: str
    agent_responses: List[AgentResponse]
    debate: DebateInfo
    status: str

class FinalSynthesisResponse(BaseModel):
    type: str
    overall_recommendation: str
    executive_summary: str
    key_findings: List[str]
    meta_analysis: str
    markdown_report: str

# ================================================================================
# ENDPOINT 1: UPLOAD & EXTRACT FACTORS
# ================================================================================

@app.post("/upload", response_model=UploadResponse)
def upload_document(request: UploadRequest):
    """Upload document and extract factors immediately"""
    if not request.report_text or len(request.report_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Report text must be at least 50 characters")
    
    doc_id = f"doc_{str(uuid.uuid4())[:8]}"
    logger.info(f"📄 Document uploaded: {doc_id}")
    log_event(f"Document {doc_id[:8]} uploaded", "📄")
    
    update_progress(doc_id, "Extracting factors...", 10, "🔍")
    factors = extract_factors(request.report_text)
    update_progress(doc_id, "Factors extracted", 100, "✓")
    
    documents[doc_id] = {
        "document_id": doc_id,
        "report_text": request.report_text,
        "factors": factors,
        "enable_web_scraping": request.enable_web_scraping,
        "created_at": datetime.now().isoformat(),
        "factor_results": {}
    }
    
    factor_list = [FactorInfo(id=i+1, title=factor) for i, factor in enumerate(factors)]
    logger.info(f"✓ Extracted {len(factors)} factors")
    complete_task(doc_id, f"Document {doc_id[:8]}: {len(factors)} factors extracted")
    
    return UploadResponse(
        status="success",
        document_id=doc_id,
        factors=factor_list,
        total_factors=len(factors)
    )

# ================================================================================
# ENDPOINT 2: ANALYZE SINGLE FACTOR
# ================================================================================

def process_single_factor(doc_id: str, factor_id: int):
    """Background task to process a single factor"""
    job_id = f"{doc_id}_f{factor_id}"
    try:
        doc = documents[doc_id]
        factor = doc["factors"][factor_id - 1]
        report_text = doc["report_text"]
        enable_web_scraping = doc.get("enable_web_scraping", True)
        
        logger.info(f"⚔️ Analyzing factor {factor_id}: {factor}")
        update_progress(job_id, f"Starting analysis", 0, "🚀")
        
        update_progress(job_id, f"Collecting evidence...", 10, "🔍")
        evidence = collect_all_evidence(factor, enable_scraping=enable_web_scraping)
        update_progress(job_id, f"Evidence collected", 25, "✓")
        
        update_progress(job_id, f"Running debate...", 30, "⚔️")
        debate_transcript = run_debate(report_text, factor, evidence)
        update_progress(job_id, f"Debate complete", 60, "✓")
        
        update_progress(job_id, f"Anonymizing...", 65, "🔒")
        anonymized_transcript = anonymize_transcript(debate_transcript)
        
        update_progress(job_id, f"Peer reviews...", 70, "👥")
        peer_reviews = collect_peer_reviews(anonymized_transcript)
        update_progress(job_id, f"Reviews complete", 85, "✓")
        
        update_progress(job_id, f"Judge synthesis...", 90, "⚖️")
        verdict = judge_synthesis(factor, debate_transcript, peer_reviews)
        update_progress(job_id, f"Complete", 95, "✓")
        
        agent_responses = _extract_agent_responses(debate_transcript)
        peer_scores = _calculate_peer_scores(peer_reviews)
        pro_arg, con_arg = _extract_pro_con_arguments(debate_transcript)
        verdict_structured = _parse_verdict(verdict)
        
        result_key = f"{doc_id}_factor_{factor_id}"
        factor_results[result_key] = {
            "factor_id": factor_id,
            "factor_title": factor,
            "agent_responses": agent_responses,
            "debate": {
                "pro_argument": pro_arg,
                "con_argument": con_arg,
                "judge_verdict": verdict_structured,
                "peer_review_scores": peer_scores
            },
            "status": "complete",
            "raw_verdict": verdict,
            "peer_reviews": peer_reviews
        }
        
        documents[doc_id]["factor_results"][factor_id] = result_key
        logger.info(f"✅ Factor {factor_id} complete")
        complete_task(job_id, f"Factor {factor_id} complete: {verdict_structured.verdict[:30]}...")
        
    except Exception as e:
        logger.error(f"❌ Factor {factor_id} failed: {e}")
        error_task(job_id, f"Factor {factor_id} failed: {str(e)[:50]}")
        result_key = f"{doc_id}_factor_{factor_id}"
        factor_results[result_key] = {
            "factor_id": factor_id,
            "status": "error",
            "error": str(e)
        }

@app.post("/analyze/factor/{doc_id}/{factor_id}")
def analyze_factor(doc_id: str, factor_id: int, background_tasks: BackgroundTasks):
    """Start analysis of a specific factor"""
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    if factor_id < 1 or factor_id > len(doc["factors"]):
        raise HTTPException(status_code=400, detail="Invalid factor ID")
    
    background_tasks.add_task(process_single_factor, doc_id, factor_id)
    
    return {
        "status": "processing",
        "factor_id": factor_id,
        "message": f"Analysis started for factor {factor_id}"
    }

@app.get("/analyze/factor/{doc_id}/{factor_id}")
def get_factor_analysis(doc_id: str, factor_id: int):
    """Get analysis results for a specific factor"""
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    result_key = f"{doc_id}_factor_{factor_id}"
    
    # If analysis hasn't been started or completed yet
    if result_key not in factor_results:
        return {
            "status": "pending",
            "factor_id": factor_id,
            "message": "Analysis not started or still in progress"
        }
    
    result = factor_results[result_key]
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
    
    # Return processing status if still running
    if result.get("status") != "complete":
        return {
            "status": "processing",
            "factor_id": factor_id,
            "message": "Analysis in progress"
        }
    
    return FactorAnalysisResponse(**result)

# ================================================================================
# ENDPOINT 3: FINAL SYNTHESIS
# ================================================================================

@app.get("/synthesis/{doc_id}", response_model=FinalSynthesisResponse)
def get_final_synthesis(doc_id: str):
    """Get final synthesis after all factors analyzed"""
    log_event(f"Synthesis for {doc_id[:8]}", "📊")
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    total_factors = len(doc["factors"])
    completed_factors = len(doc["factor_results"])
    
    if completed_factors < total_factors:
        raise HTTPException(
            status_code=400, 
            detail=f"Not all factors analyzed ({completed_factors}/{total_factors})"
        )
    
    all_results = []
    for factor_id in range(1, total_factors + 1):
        result_key = doc["factor_results"][factor_id]
        all_results.append(factor_results[result_key])
    
    # Generate markdown report file
    markdown_content = _save_markdown_report(doc_id, doc["report_text"], all_results)
    
    final_report_data = _generate_synthesis(doc["report_text"], all_results)
    final_report_data["markdown_report"] = markdown_content
    
    return FinalSynthesisResponse(**final_report_data)

# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def _extract_agent_responses(debate_transcript: str) -> List[AgentResponse]:
    """Extract agent responses from transcript"""
    responses = []
    lines = debate_transcript.split('\n')
    current_agent = None
    current_text = []
    
    for line in lines:
        if line.startswith('[') and ']' in line:
            if current_agent and current_text:
                responses.append(AgentResponse(
                    agent_id=current_agent,
                    response=' '.join(current_text).strip()
                ))
            current_agent = line.split('[')[1].split(']')[0]
            current_text = [line.split(']:')[-1].strip() if ']:' in line else '']
        elif current_agent and line.strip():
            current_text.append(line.strip())
    
    if current_agent and current_text:
        responses.append(AgentResponse(
            agent_id=current_agent,
            response=' '.join(current_text).strip()
        ))
    
    return responses[:4]

def _calculate_peer_scores(peer_reviews: dict) -> List[PeerReviewScore]:
    """Calculate average scores"""
    agent_scores = {}
    
    for model, reviews in peer_reviews.items():
        for agent_id, scores in reviews.items():
            if agent_id not in agent_scores:
                agent_scores[agent_id] = []
            
            if isinstance(scores, dict):
                numeric_scores = [v for k, v in scores.items() if k != 'critique' and isinstance(v, (int, float))]
                if numeric_scores:
                    avg = sum(numeric_scores) / len(numeric_scores)
                    agent_scores[agent_id].append(avg)
    
    result = []
    for agent_id, scores_list in agent_scores.items():
        if scores_list:
            result.append(PeerReviewScore(
                agent_id=agent_id.replace("Agent-", "A-"),
                score=round(sum(scores_list) / len(scores_list), 1)
            ))
    
    return result

def _extract_pro_con_arguments(debate_transcript: str) -> tuple:
    """Extract pro/con summaries"""
    lines = debate_transcript.split('\n')
    pro_args = []
    con_args = []
    
    for line in lines:
        if '(PRO)' in line or 'Pro-' in line:
            pro_args.append(line)
        elif '(CON)' in line or 'Con-' in line:
            con_args.append(line)
    
    pro_summary = ' '.join(pro_args[:2])[:500] if pro_args else "Pro arguments presented..."
    con_summary = ' '.join(con_args[:2])[:500] if con_args else "Con arguments presented..."
    
    return pro_summary, con_summary

def _parse_verdict(verdict_text: str) -> JudgeVerdict:
    """Parse verdict into structured format"""
    lines = verdict_text.split('\n')
    verdict = None
    reasoning = verdict_text
    confidence = 5
    
    # Try to find structured verdict
    for line in lines:
        if 'VERDICT:' in line.upper():
            verdict = line.split(':')[-1].strip()
        elif 'CONFIDENCE:' in line.upper():
            try:
                confidence = int(''.join(filter(str.isdigit, line))[:2])
                confidence = min(10, max(1, confidence))
            except:
                confidence = 5
    
    # If no structured verdict found, extract from first few lines
    if not verdict:
        first_lines = ' '.join(lines[:5]).lower()
        
        # Check for positive indicators
        if any(word in first_lines for word in ['positive', 'achievable', 'feasible', 'recommended', 'proceed', 'viable', 'support']):
            verdict = "POSITIVE"
        # Check for negative indicators
        elif any(word in first_lines for word in ['negative', 'not feasible', 'high risk', 'not recommended', 'oppose', 'reject', 'insufficient']):
            verdict = "NEGATIVE"
        # Last resort - use first sentence
        else:
            verdict = lines[0][:100] if lines else "UNABLE TO PARSE"
    
    return JudgeVerdict(
        verdict=verdict,
        reasoning=reasoning,
        confidence=confidence
    )

def _save_markdown_report(doc_id: str, report_text: str, all_results: List[dict]):
    """Generate and save markdown report file"""
    report = []
    report.append("# PROJECT AETHER - FINAL REPORT")
    report.append("=" * 80)
    report.append("")
    report.append("## ORIGINAL REPORT")
    report.append(report_text[:500] + "...")
    report.append("")
    report.append("=" * 80)
    report.append("")
    
    for idx, result in enumerate(all_results, 1):
        report.append(f"## FACTOR {idx}: {result['factor_title']}")
        report.append("")
        report.append("### JUDGE'S VERDICT")
        report.append(result['raw_verdict'])
        report.append("")
        report.append("### PEER REVIEW SCORES")
        
        # Aggregate peer scores
        for agent_num in range(1, 5):
            agent_id = f"Agent-{agent_num}"
            scores = []
            for model, reviews in result['peer_reviews'].items():
                if agent_id in reviews:
                    agent_scores = reviews[agent_id]
                    if isinstance(agent_scores, dict):
                        avg = sum([v for k, v in agent_scores.items() if k != 'critique' and isinstance(v, (int, float))]) / 5
                        scores.append(avg)
            
            if scores:
                avg_score = sum(scores) / len(scores)
                report.append(f"- {agent_id}: {avg_score:.1f}/10")
        
        report.append("")
        report.append("---")
        report.append("")
    
    report.append("=" * 80)
    report.append("## META-ANALYSIS")
    report.append("")
    report.append("This report represents a stress-test of the original proposal.")
    report.append("Verdicts are based on argument quality, not consensus.")
    report.append("All reasoning is auditable through saved transcripts.")
    report.append("")
    report.append("=" * 80)
    
    # Save to outputs folder
    markdown_content = "\n".join(report)
    output_file = f"outputs/final_report_{doc_id}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    logger.info(f"📝 Markdown report saved: {output_file}")
    complete_task(doc_id, f"Report saved to {output_file}")
    
    return markdown_content

def _generate_synthesis(report_text: str, all_results: List[dict]) -> dict:
    """Generate final synthesis"""
    # Analyze verdicts more intelligently
    positive_keywords = ['achievable', 'feasible', 'viable', 'proceed', 'recommended', 'strong', 'positive']
    negative_keywords = ['risky', 'unfeasible', 'not achievable', 'high risk', 'significant concern', 'critical issue']
    
    positive_count = 0
    negative_count = 0
    
    for r in all_results:
        verdict_text = r['raw_verdict'].lower()
        # Check for positive indicators
        if any(kw in verdict_text for kw in positive_keywords):
            positive_count += 1
        # Check for negative indicators
        elif any(kw in verdict_text for kw in negative_keywords):
            negative_count += 1
    
    if positive_count > negative_count:
        recommendation = "PROCEED_WITH_CAUTION"
    elif negative_count > positive_count:
        recommendation = "HIGH_RISK"
    else:
        recommendation = "NEEDS_FURTHER_ANALYSIS"
    
    exec_summary = f"Based on analysis of {len(all_results)} factors, " \
                   f"{positive_count} positive and {negative_count} negative assessments."
    
    # Use the structured verdict for cleaner key findings
    findings = [
        f"{r['factor_title']}: {r['debate']['judge_verdict'].verdict}"
        for r in all_results[:3]
    ]
    
    meta_analysis = "This report represents a stress-test through adversarial debate, peer review, and holistic judgment."
    
    return {
        "type": "final_synthesis",
        "overall_recommendation": recommendation,
        "executive_summary": exec_summary,
        "key_findings": findings,
        "meta_analysis": meta_analysis
    }

# ================================================================================
# HEALTH CHECK
# ================================================================================

@app.get("/")
def root():
    return {
        "service": "Project AETHER API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "upload": "POST /upload",
            "analyze_factor": "POST /analyze/factor/{doc_id}/{factor_id}",
            "get_factor": "GET /analyze/factor/{doc_id}/{factor_id}",
            "synthesis": "GET /synthesis/{doc_id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AETHER API on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
