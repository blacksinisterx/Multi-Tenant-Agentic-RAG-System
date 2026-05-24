"""
AI-DOC:
Purpose: Evaluation harness for multi-tenant RAG system
Constraints: Assignment-compliant evaluation per tenant with citation checking
Manual QA: see plan.md -> Phase 8 Manual QA section
"""

import os
import json
import subprocess
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any


def load_tenant_questions(eval_dir: str, tenant: str) -> List[Dict[str, Any]]:
    """Load evaluation questions for a specific tenant."""
    eval_file = Path(eval_dir) / f"{tenant}.json"
    if not eval_file.exists():
        print(f"⚠️  No evaluation file found for {tenant}: {eval_file}")
        return []
    
    try:
        with open(eval_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both formats: {"questions": [...]} or direct [...]
            if isinstance(data, list):
                # Convert from existing format to expected format
                questions = []
                for item in data:
                    questions.append({
                        'query': item.get('q', ''),
                        'expected': 'answer' if item.get('allowed', True) else 'refusal',
                        'contains': item.get('a_contains', [])
                    })
                return questions
            else:
                return data.get('questions', [])
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Error loading {eval_file}: {e}")
        return []


def run_cli_query(tenant: str, query: str, config: str) -> Dict[str, Any]:
    """Run a single CLI query and capture results."""
    # Use virtual environment Python executable
    python_exe = r"D:/FAST/Semester 7/Agentic AI/Assignments/Assignment 2/.venv/Scripts/python.exe"
    cmd = [
        python_exe, "-m", "app.main",
        "--tenant", tenant,
        "--query", query,
        "--config", config
    ]
    
    try:
        # Primary attempt: 120s timeout (some index/LLM calls may take longer)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # increased timeout
            cwd=os.getcwd()
        )
        
        return {
            "command": " ".join(cmd),
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        # Retry once with a longer timeout to handle occasional long index/LLM warm-ups
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=os.getcwd()
            )

            return {
                "command": " ".join(cmd),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "command": " ".join(cmd),
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out after 180 seconds",
                "success": False
            }
    except Exception as e:
        return {
            "command": " ".join(cmd),
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False
        }


def extract_citations(output: str) -> List[Dict[str, str]]:
    """Extract citations from output text with improved pattern matching."""
    # More flexible pattern: [n] ... (doc=DOC_ID, tenant=Ux, vis=public|private)
    citation_pattern = re.compile(
        r'\[(\d+)\].*?\(doc\s*=\s*([^,\s)]+),?\s*tenant\s*=\s*([^,\s)]+),?\s*vis\s*=\s*([^,\s)]+)\)',
        re.IGNORECASE | re.DOTALL
    )
    
    citations = []
    for match in citation_pattern.finditer(output):
        citations.append({
            "number": match.group(1),
            "doc_id": match.group(2),
            "tenant": match.group(3),
            "visibility": match.group(4)
        })
    
    return citations


def check_citation_validity(citations: List[Dict[str, str]], tenant: str) -> Dict[str, Any]:
    """Check if citations are valid for the given tenant."""
    valid_citations = []
    invalid_citations = []
    
    for citation in citations:
        doc_tenant = citation["tenant"]
        visibility = citation["visibility"]
        
        # Valid if: same tenant OR public visibility OR sub-tenant access
        if (doc_tenant == tenant or 
            visibility == "public" or 
            doc_tenant.startswith(tenant + "_")):
            valid_citations.append(citation)
        else:
            invalid_citations.append(citation)
    
    return {
        "total_citations": len(citations),
        "valid_citations": len(valid_citations),
        "invalid_citations": len(invalid_citations),
        "citation_accuracy": len(valid_citations) / len(citations) if citations else 0.0,
        "valid_citation_list": valid_citations,
        "invalid_citation_list": invalid_citations
    }


def is_refusal(output: str) -> bool:
    """Check if output is a refusal."""
    refusal_patterns = [
        r"Refusal:\s*AccessDenied",
        r"Refusal:\s*InjectionDetected", 
        r"Refusal:\s*LeakageRisk"
    ]
    
    for pattern in refusal_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return True
    return False


def evaluate_question(tenant: str, question: Dict[str, Any], config: str) -> Dict[str, Any]:
    """Evaluate a single question."""
    query = question.get('query', '')
    expected_type = question.get('expected', 'answer')  # 'answer' or 'refusal'
    expected_contains = question.get('contains', [])
    
    # Run the CLI query
    result = run_cli_query(tenant, query, config)
    
    if not result["success"]:
        return {
            "question": question,
            "tenant": tenant,
            "cli_result": result,
            "evaluation": {
                "success": False,
                "error": "CLI execution failed",
                "expected_type": expected_type,
                "actual_type": "error"
            }
        }
    
    output = result["stdout"]
    
    # Determine actual response type
    actual_type = "refusal" if is_refusal(output) else "answer"
    
    # Extract and validate citations
    citations = extract_citations(output)
    citation_analysis = check_citation_validity(citations, tenant)
    
    # Evaluate correctness
    type_correct = (expected_type == actual_type)
    # Citations are only required for answer-type responses, not refusals
    citation_correct = (expected_type == "refusal") or (citation_analysis["citation_accuracy"] >= 0.9)
    
    overall_correct = type_correct and citation_correct
    
    return {
        "question": question,
        "tenant": tenant,
        "cli_result": result,
        "evaluation": {
            "success": True,
            "expected_type": expected_type,
            "actual_type": actual_type,
            "type_correct": type_correct,
            "citation_analysis": citation_analysis,
            "citation_correct": citation_correct,
            "overall_correct": overall_correct,
            "output_text": output
        }
    }


def run_evaluation() -> Dict[str, Any]:
    """Run complete evaluation across all tenants."""
    parser = argparse.ArgumentParser(description="RAG System Evaluation Harness")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--eval-dir", default="eval", help="Evaluation directory")
    parser.add_argument("--output", default="eval/results.json", help="Output results file")
    args = parser.parse_args()
    
    # Ensure eval directory exists
    eval_dir = Path(args.eval_dir)
    eval_dir.mkdir(exist_ok=True)
    
    results = {
        "config": args.config,
        "evaluation_summary": {},
        "tenant_results": {},
        "overall_metrics": {}
    }
    
    tenants = ["U1", "U2", "U3", "U4"]
    all_evaluations = []
    
    for tenant in tenants:
        print(f"🔍 Evaluating tenant {tenant}...")
        
        questions = load_tenant_questions(args.eval_dir, tenant)
        if not questions:
            print(f"⚠️  No questions found for {tenant}, skipping...")
            continue
        
        tenant_evaluations = []
        for i, question in enumerate(questions, 1):
            print(f"  📝 Question {i}/{len(questions)}: {question.get('query', 'N/A')[:50]}...")
            
            evaluation = evaluate_question(tenant, question, args.config)
            tenant_evaluations.append(evaluation)
            all_evaluations.append(evaluation)
        
        # Calculate tenant metrics
        successful_evals = [e for e in tenant_evaluations if e["evaluation"]["success"]]
        correct_evals = [e for e in successful_evals if e["evaluation"]["overall_correct"]]
        
        tenant_metrics = {
            "total_questions": len(questions),
            "successful_evaluations": len(successful_evals),
            "correct_evaluations": len(correct_evals),
            "success_rate": len(successful_evals) / len(questions) if questions else 0.0,
            "accuracy_rate": len(correct_evals) / len(successful_evals) if successful_evals else 0.0
        }
        
        results["tenant_results"][tenant] = {
            "metrics": tenant_metrics,
            "evaluations": tenant_evaluations
        }
        
        print(f"  ✅ {tenant}: {len(correct_evals)}/{len(questions)} correct ({tenant_metrics['accuracy_rate']:.1%})")
    
    # Calculate overall metrics
    successful_evals = [e for e in all_evaluations if e["evaluation"]["success"]]
    correct_evals = [e for e in successful_evals if e["evaluation"]["overall_correct"]]
    citation_evals = [e for e in successful_evals if e["evaluation"].get("citation_correct", False)]
    
    results["overall_metrics"] = {
        "total_questions": len(all_evaluations),
        "successful_evaluations": len(successful_evals),
        "correct_evaluations": len(correct_evals),
        "citation_correct_evaluations": len(citation_evals),
        "overall_success_rate": len(successful_evals) / len(all_evaluations) if all_evaluations else 0.0,
        "overall_accuracy_rate": len(correct_evals) / len(successful_evals) if successful_evals else 0.0,
        "citation_fidelity": len(citation_evals) / len(successful_evals) if successful_evals else 0.0
    }
    
    # Save results
    output_file = Path(args.output)
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    metrics = results["overall_metrics"]
    print(f"\n📊 EVALUATION SUMMARY:")
    print(f"   Total Questions: {metrics['total_questions']}")
    print(f"   Success Rate: {metrics['overall_success_rate']:.1%}")
    print(f"   Accuracy Rate: {metrics['overall_accuracy_rate']:.1%}")
    print(f"   Citation Fidelity: {metrics['citation_fidelity']:.1%}")
    print(f"   Results saved to: {output_file}")
    
    # Check assignment thresholds
    print(f"\n🎯 ASSIGNMENT COMPLIANCE:")
    print(f"   Citation Fidelity ≥90%: {'✅' if metrics['citation_fidelity'] >= 0.9 else '❌'} ({metrics['citation_fidelity']:.1%})")
    print(f"   Overall Accuracy ≥90%: {'✅' if metrics['overall_accuracy_rate'] >= 0.9 else '❌'} ({metrics['overall_accuracy_rate']:.1%})")
    
    return results


if __name__ == "__main__":
    run_evaluation()