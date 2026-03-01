
"""
AETHER Benchmarking Suite
Measures consistency, accuracy, and performance metrics for multi-agent debate system.
"""

import json
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter
import statistics

from evidence_collector import collect_all_evidence
from debate_engine import run_debate
from peer_review import anonymize_transcript, collect_peer_reviews
from judge import judge_synthesis
from llm_client import call_llm
import config


class BenchmarkRunner:
    """Runs benchmarks and collects performance metrics."""
    
    def __init__(self, output_dir: str = "benchmarks"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def run_aether_analysis(self, content: str, use_web_search: bool = False) -> tuple:
        """
        Run AETHER analysis on content.
        Returns: (verdict, duration)
        """
        start_time = time.time()
        
        # Evidence collection (optional)
        evidence = {"pro": [], "con": []}
        if use_web_search:
            topic = content[:200].replace("\n", " ")
            evidence = collect_all_evidence(topic, enable_scraping=True)
        
        # Debate (use content as both report and factor for simplicity)
        factor = content[:100] + "..."
        debate_transcript = run_debate(
            report=content,
            factor=factor,
            evidence=evidence,
            agent_count=5
        )
        
        # Anonymize
        anonymized = anonymize_transcript(debate_transcript)
        
        # Peer review
        reviews = collect_peer_reviews(anonymized, agent_count=5)
        
        # Judge synthesis
        verdict = judge_synthesis(factor, debate_transcript, reviews)
        
        duration = time.time() - start_time
        return verdict, duration
        
    def run_consistency_test(self, prompts: List[str], runs_per_prompt: int = 3) -> Dict[str, Any]:
        """
        Test consistency by running the same prompts multiple times.
        
        Args:
            prompts: List of test prompts
            runs_per_prompt: Number of times to run each prompt
            
        Returns:
            Dictionary with consistency metrics
        """
        print(f"\n{'='*60}")
        print("CONSISTENCY TEST")
        print(f"{'='*60}")
        print(f"Prompts: {len(prompts)}")
        print(f"Runs per prompt: {runs_per_prompt}")
        print(f"Total runs: {len(prompts) * runs_per_prompt}\n")
        
        results = []
        
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] Testing: {prompt[:60]}...")
            prompt_results = []
            
            for run in range(runs_per_prompt):
                print(f"  Run {run + 1}/{runs_per_prompt}...", end=" ")
                
                try:
                    # Run AETHER analysis
                    verdict, duration = self.run_aether_analysis(prompt, use_web_search=False)
                    
                    # Extract verdict (POSITIVE/NEGATIVE)
                    verdict_type = "POSITIVE" if "POSITIVE" in verdict.upper() else "NEGATIVE"
                    
                    prompt_results.append({
                        "verdict": verdict_type,
                        "full_verdict": verdict,
                        "duration": duration,
                        "run": run + 1
                    })
                    
                    print(f"✓ {verdict_type} ({duration:.1f}s)")
                    
                except Exception as e:
                    print(f"✗ Error: {e}")
                    prompt_results.append({
                        "verdict": "ERROR",
                        "full_verdict": str(e),
                        "duration": 0,
                        "run": run + 1
                    })
            
            # Calculate consistency for this prompt
            verdicts = [r["verdict"] for r in prompt_results if r["verdict"] != "ERROR"]
            if verdicts:
                most_common = Counter(verdicts).most_common(1)[0][0]
                agreement = verdicts.count(most_common) / len(verdicts)
            else:
                agreement = 0.0
            
            results.append({
                "prompt": prompt,
                "runs": prompt_results,
                "agreement": agreement,
                "avg_duration": statistics.mean([r["duration"] for r in prompt_results if r["duration"] > 0]) if any(r["duration"] > 0 for r in prompt_results) else 0
            })
        
        # Calculate overall metrics
        all_agreements = [r["agreement"] for r in results]
        agreement_rate = statistics.mean(all_agreements) * 100 if all_agreements else 0
        
        # Calculate flip rate (how often verdicts changed)
        flip_count = sum(1 for r in results if r["agreement"] < 1.0)
        flip_rate = (flip_count / len(results)) * 100 if results else 0
        
        avg_duration = statistics.mean([r["avg_duration"] for r in results if r["avg_duration"] > 0]) if results else 0
        
        metrics = {
            "test_type": "consistency",
            "timestamp": datetime.now().isoformat(),
            "prompts_tested": len(prompts),
            "runs_per_prompt": runs_per_prompt,
            "total_runs": len(prompts) * runs_per_prompt,
            "agreement_rate": round(agreement_rate, 1),
            "flip_rate": round(flip_rate, 1),
            "avg_duration_seconds": round(avg_duration, 1),
            "detailed_results": results
        }
        
        # Save results
        filename = f"{self.output_dir}/consistency_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n{'='*60}")
        print("RESULTS:")
        print(f"{'='*60}")
        print(f"Agreement Rate: {agreement_rate:.1f}% (same verdict across runs)")
        print(f"Flip Rate: {flip_rate:.1f}% (prompts with inconsistent verdicts)")
        print(f"Avg Duration: {avg_duration:.1f}s per analysis")
        print(f"\nResults saved to: {filename}")
        
        return metrics
    
    def run_baseline_comparison(self, test_cases: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Compare AETHER against single-LLM baselines.
        
        Args:
            test_cases: List of dicts with 'prompt' and optional 'ground_truth'
            
        Returns:
            Dictionary with comparison metrics
        """
        print(f"\n{'='*60}")
        print("BASELINE COMPARISON TEST")
        print(f"{'='*60}")
        print(f"Test cases: {len(test_cases)}\n")
        
        results = []
        
        for i, case in enumerate(test_cases, 1):
            prompt = case["prompt"]
            ground_truth = case.get("ground_truth")
            
            print(f"\n[{i}/{len(test_cases)}] {prompt[:60]}...")
            case_results = {"prompt": prompt, "ground_truth": ground_truth}
            
            # Test AETHER (multi-agent)
            print("  AETHER (5-agent)...", end=" ")
            try:
                verdict, duration = self.run_aether_analysis(prompt, use_web_search=False)
                verdict_type = "POSITIVE" if "POSITIVE" in verdict.upper() else "NEGATIVE"
                case_results["aether"] = {
                    "verdict": verdict_type,
                    "duration": duration,
                    "full_text": verdict
                }
                print(f"✓ {verdict_type} ({duration:.1f}s)")
            except Exception as e:
                case_results["aether"] = {"verdict": "ERROR", "duration": 0, "error": str(e)}
                print(f"✗ Error")
            
            # Test Single LLM Solo (single call)
            print("  Single LLM Solo...", end=" ")
            start = time.time()
            try:
                # Use the same model as Pro agents for fair comparison
                solo_verdict = call_llm(
                    model_spec=config.PRO_MODEL_1,
                    prompt=f"Analyze this statement and determine if it's valid. Provide a verdict (POSITIVE if valid/true, NEGATIVE if invalid/false):\n\n{prompt}",
                    system_prompt="You are an analytical judge. Provide clear verdicts."
                )
                verdict_type = "POSITIVE" if "POSITIVE" in solo_verdict.upper() else "NEGATIVE"
                case_results["single_llm"] = {
                    "verdict": verdict_type,
                    "duration": time.time() - start,
                    "full_text": solo_verdict
                }
                print(f"✓ {verdict_type} ({time.time() - start:.1f}s)")
            except Exception as e:
                case_results["single_llm"] = {"verdict": "ERROR", "duration": 0, "error": str(e)}
                print(f"✗ Error")
            
            results.append(case_results)
        
        # Calculate metrics
        aether_correct = 0
        single_llm_correct = 0
        total_with_truth = 0
        
        for r in results:
            if r.get("ground_truth"):
                total_with_truth += 1
                if r["aether"]["verdict"] == r["ground_truth"]:
                    aether_correct += 1
                if r["single_llm"]["verdict"] == r["ground_truth"]:
                    single_llm_correct += 1
        
        aether_durations = [r["aether"]["duration"] for r in results if r["aether"]["duration"] > 0]
        single_llm_durations = [r["single_llm"]["duration"] for r in results if r["single_llm"]["duration"] > 0]
        
        metrics = {
            "test_type": "baseline_comparison",
            "timestamp": datetime.now().isoformat(),
            "test_cases": len(test_cases),
            "cases_with_ground_truth": total_with_truth,
            "aether": {
                "accuracy": round((aether_correct / total_with_truth * 100), 1) if total_with_truth > 0 else None,
                "avg_duration": round(statistics.mean(aether_durations), 1) if aether_durations else 0
            },
            "single_llm": {
                "accuracy": round((single_llm_correct / total_with_truth * 100), 1) if total_with_truth > 0 else None,
                "avg_duration": round(statistics.mean(single_llm_durations), 1) if single_llm_durations else 0
            },
            "detailed_results": results
        }
        
        # Save results
        filename = f"{self.output_dir}/comparison_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n{'='*60}")
        print("RESULTS:")
        print(f"{'='*60}")
        if total_with_truth > 0:
            print(f"AETHER Accuracy: {metrics['aether']['accuracy']}% ({aether_correct}/{total_with_truth})")
            print(f"Single LLM Accuracy: {metrics['single_llm']['accuracy']}% ({single_llm_correct}/{total_with_truth})")
            print(f"Improvement: +{metrics['aether']['accuracy'] - metrics['single_llm']['accuracy']:.1f}%")
        print(f"\nAETHER Avg Time: {metrics['aether']['avg_duration']:.1f}s")
        print(f"Single LLM Avg Time: {metrics['single_llm']['avg_duration']:.1f}s")
        print(f"\nResults saved to: {filename}")
        
        return metrics
    
    def generate_report(self, metrics_files: Optional[List[str]] = None) -> str:
        """
        Generate a markdown report from benchmark results.
        
        Args:
            metrics_files: List of JSON files to include. If None, uses all files in output_dir
        """
        if metrics_files is None:
            metrics_files = [
                os.path.join(self.output_dir, f) 
                for f in os.listdir(self.output_dir) 
                if f.endswith('.json')
            ]
        
        report_lines = [
            "# AETHER Benchmark Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n## Summary\n",
        ]
        
        consistency_results = []
        comparison_results = []
        
        for filepath in metrics_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if data["test_type"] == "consistency":
                        consistency_results.append(data)
                    elif data["test_type"] == "baseline_comparison":
                        comparison_results.append(data)
            except Exception as e:
                print(f"Warning: Could not load {filepath}: {e}")
        
        # Consistency section
        if consistency_results:
            report_lines.append("### Consistency Metrics\n")
            for result in consistency_results:
                report_lines.append(f"**Test Date:** {result['timestamp'][:10]}")
                report_lines.append(f"- Agreement Rate: **{result['agreement_rate']}%**")
                report_lines.append(f"- Flip Rate: **{result['flip_rate']}%**")
                report_lines.append(f"- Avg Duration: **{result['avg_duration_seconds']}s**")
                report_lines.append(f"- Test Cases: {result['prompts_tested']} × {result['runs_per_prompt']} runs\n")
        
        # Comparison section
        if comparison_results:
            report_lines.append("### Baseline Comparison\n")
            for result in comparison_results:
                report_lines.append(f"**Test Date:** {result['timestamp'][:10]}")
                if result['aether']['accuracy'] is not None:
                    report_lines.append(f"- AETHER Accuracy: **{result['aether']['accuracy']}%**")
                    report_lines.append(f"- Single LLM Accuracy: **{result['single_llm']['accuracy']}%**")
                    improvement = result['aether']['accuracy'] - result['single_llm']['accuracy']
                    report_lines.append(f"- Improvement: **+{improvement:.1f}%**")
                report_lines.append(f"- AETHER Avg Time: {result['aether']['avg_duration']}s")
                report_lines.append(f"- Single LLM Avg Time: {result['single_llm']['avg_duration']}s\n")
        
        report_content = "\n".join(report_lines)
        
        # Save report
        report_file = f"{self.output_dir}/BENCHMARK_REPORT.md"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"\nReport saved to: {report_file}")
        return report_content


def main():
    """Run sample benchmarks."""
    runner = BenchmarkRunner()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║           AETHER BENCHMARKING SUITE                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("\nSelect benchmark type:")
    print("1. Consistency Test (same prompts, multiple runs)")
    print("2. Baseline Comparison (AETHER vs Single LLM)")
    print("3. Generate Report from existing results")
    print("4. Run Full Benchmark Suite")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        # Sample consistency test
        test_prompts = [
            "Nuclear energy is the key to solving climate change",
            "Remote work decreases productivity in software teams",
            "AI will replace most creative jobs by 2030",
            "Universal basic income should be implemented globally",
            "Cryptocurrency is the future of finance"
        ]
        
        runs = int(input("Runs per prompt (default 3): ").strip() or "3")
        runner.run_consistency_test(test_prompts, runs_per_prompt=runs)
        
    elif choice == "2":
        # Sample comparison test
        test_cases = [
            {
                "prompt": "Nuclear energy is safer than fossil fuels",
                "ground_truth": "POSITIVE"  # Based on safety statistics
            },
            {
                "prompt": "Remote work reduces employee engagement",
                "ground_truth": "NEGATIVE"  # Studies show mixed results
            },
            {
                "prompt": "Solar panels have a positive ROI within 5 years",
                "ground_truth": "POSITIVE"  # Industry data confirms
            }
        ]
        
        runner.run_baseline_comparison(test_cases)
        
    elif choice == "3":
        runner.generate_report()
        
    elif choice == "4":
        print("\nRunning full benchmark suite...")
        
        # Consistency test
        consistency_prompts = [
            "AI will replace most jobs in the next decade",
            "Electric vehicles are better for the environment than gas cars",
            "Working from home increases productivity"
        ]
        runner.run_consistency_test(consistency_prompts, runs_per_prompt=3)
        
        # Baseline comparison
        comparison_cases = [
            {"prompt": "Solar energy is cost-effective", "ground_truth": "POSITIVE"},
            {"prompt": "Social media harms mental health", "ground_truth": "POSITIVE"}
        ]
        runner.run_baseline_comparison(comparison_cases)
        
        # Generate report
        runner.generate_report()
        
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
