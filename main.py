#!/usr/bin/env python3
"""
Project AETHER - Multi-Agent Debate System
A reasoning stress-test pipeline using adversarial debate.
"""

import os
import json
import sys
import logging
from datetime import datetime

import config
from clean_logging import setup_logging
from factor_extraction import extract_factors
from evidence_collector import collect_all_evidence
from debate_engine import run_debate
from peer_review import anonymize_transcript, collect_peer_reviews
from judge import judge_synthesis, generate_final_report

# Setup clean logging (logs to file, minimal terminal output)
logger, log_file = setup_logging("aether_analysis")

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    if not os.path.exists(config.OUTPUT_DIR):
        os.makedirs(config.OUTPUT_DIR)

def main(report_file_path):
    """
    Main orchestrator for the AETHER system.
    """
    print("=" * 80)
    print("PROJECT AETHER - Reasoning Stress-Test Pipeline")
    print("=" * 80)
    print()
    
    # Ensure output directory exists
    ensure_output_dir()
    
    # 1. Load report
    print("📄 Loading report...")
    with open(report_file_path, 'r', encoding='utf-8') as f:
        report_text = f.read()
    print(f"Report loaded: {len(report_text)} characters")
    print()
    
    # 2. Extract factors
    print("🔍 Extracting debatable factors...")
    factors = extract_factors(report_text)
    print(f"Extracted {len(factors)} factors:")
    for i, factor in enumerate(factors, 1):
        print(f"  {i}. {factor}")
    print()
    
    # 3. Process each factor
    all_factor_results = []
    
    for idx, factor in enumerate(factors, 1):
        print("=" * 80)
        print(f"PROCESSING FACTOR {idx}/{len(factors)}: {factor}")
        print("=" * 80)
        print()
        
        # 3a. Collect evidence
        print("🌐 Collecting evidence (Pro & Con)...")
        evidence = collect_all_evidence(factor)
        print(f"  Pro evidence chunks: {len(evidence['pro'])}")
        print(f"  Con evidence chunks: {len(evidence['con'])}")
        print()
        
        # 3b. Run debate
        print("⚔️  Running multi-agent debate...")
        debate_transcript = run_debate(report_text, factor, evidence)
        print("Debate complete.")
        print()
        
        # 3c. Save raw transcript if enabled
        if config.SAVE_TRANSCRIPTS:
            transcript_path = os.path.join(config.OUTPUT_DIR, f"debate_factor_{idx}.txt")
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(debate_transcript)
            print(f"💾 Saved transcript: {transcript_path}")
            print()
        
        # 3d. Anonymize transcript
        print("🎭 Anonymizing transcript...")
        anonymized_transcript = anonymize_transcript(debate_transcript)
        print()
        
        # 3e. Peer review
        print("📊 Collecting peer reviews...")
        peer_reviews = collect_peer_reviews(anonymized_transcript)
        print("Peer reviews complete.")
        print()
        
        # 3f. Judge synthesis
        print("⚖️  Judge synthesis...")
        verdict = judge_synthesis(factor, debate_transcript, peer_reviews)
        print("Verdict rendered.")
        print()
        
        # Store results
        all_factor_results.append({
            'factor': factor,
            'transcript': debate_transcript,
            'peer_reviews': peer_reviews,
            'verdict': verdict
        })
    
    # 4. Generate final report
    print("=" * 80)
    print("📝 Generating final report...")
    final_report = generate_final_report(report_text, all_factor_results)
    
    # Save final report
    report_path = os.path.join(config.OUTPUT_DIR, "final_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(final_report)
    
    # Save peer reviews JSON
    reviews_path = os.path.join(config.OUTPUT_DIR, "peer_review.json")
    with open(reviews_path, 'w', encoding='utf-8') as f:
        reviews_data = {
            f"factor_{i+1}": {
                'factor': result['factor'],
                'reviews': result['peer_reviews']
            }
            for i, result in enumerate(all_factor_results)
        }
        json.dump(reviews_data, f, indent=2)
    
    print(f"✅ Final report saved: {report_path}")
    print(f"✅ Peer reviews saved: {reviews_path}")
    print()
    print("=" * 80)
    print("AETHER PROCESS COMPLETE")
    print("=" * 80)
    print()
    print("Truth is not voted. It survives attack.")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <report_file.txt>")
        print("Example: python main.py input_report.txt")
        sys.exit(1)
    
    report_file = sys.argv[1]
    
    if not os.path.exists(report_file):
        print(f"Error: File not found: {report_file}")
        sys.exit(1)
    
    main(report_file)
