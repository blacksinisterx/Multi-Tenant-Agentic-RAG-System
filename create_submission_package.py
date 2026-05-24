#!/usr/bin/env python3
"""
Final Submission Package Creator
Creates zip file with all required components for automated grading
"""

import os
import zipfile
import json
import shutil
from datetime import datetime

def create_submission_package():
    """Create the final submission package zip file"""
    
    # Define base directory
    base_dir = os.getcwd()
    submission_name = "Assignment2_LangChain_LlamaIndex_RAG_System"
    zip_filename = f"{submission_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    # Required files for submission
    required_files = [
        # Core application files
        'app/__init__.py',
        'app/main.py', 
        'app/clear_memory.py',
        
        # Agent implementation files
        'agents/__init__.py',
        'agents/controller.py',
        'agents/planner.py',
        'agents/llm.py',
        'agents/memory.py',
        'agents/langchain_flow.py',  # New LangChain integration
        
        # Retrieval system files
        'retrieval/__init__.py',
        'retrieval/index.py',
        'retrieval/search.py',
        
        # Policy and security files
        'policies/__init__.py', 
        'policies/guard.py',
        
        # Configuration files
        'config.yaml',
        '.env.example',
        'requirements.txt',
        'student_README.md',
        
        # Documentation
        'plan.md',
        'LANGCHAIN_INTEGRATION_SUMMARY.md',
        
        # Required log and evaluation files
        'logs/run.jsonl',
        'eval/redteam_results.json',
        'eval/results.json',
        
        # Data files (required for system operation)
        'data/manifest.csv',
        'data/tenant_acl.csv',
        
        # Test files
        'tests/__init__.py',
        'tests/test_acl.py',
        'tests/test_injection.py',
        'tests/test_pii.py',
        'tests/redteam_prompts.json',
        
        # Tools
        'tools/__init__.py',
        'tools/run_redteam.py',
    ]
    
    # Optional files (include if they exist)
    optional_files = [
        'eval/U1.json',
        'eval/U2.json', 
        'eval/U3.json',
        'eval/U4.json',
        'test_langchain_integration.py',  # Integration test script
    ]
    
    print(f"Creating submission package: {zip_filename}")
    print("=" * 60)
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        files_added = 0
        files_missing = []
        
        # Add required files
        for file_path in required_files:
            if os.path.exists(file_path):
                zipf.write(file_path)
                files_added += 1
                print(f"✅ Added: {file_path}")
            else:
                files_missing.append(file_path)
                print(f"❌ Missing: {file_path}")
        
        # Add optional files if they exist
        for file_path in optional_files:
            if os.path.exists(file_path):
                zipf.write(file_path)
                files_added += 1
                print(f"✅ Added (optional): {file_path}")
            else:
                print(f"ℹ️  Optional file not found: {file_path}")
    
    print("=" * 60)
    print(f"📦 Package created: {zip_filename}")
    print(f"📊 Files added: {files_added}")
    
    if files_missing:
        print(f"⚠️  Missing required files: {len(files_missing)}")
        for missing in files_missing:
            print(f"   - {missing}")
        return False
    else:
        print("✅ All required files included!")
    
    # Verify package contents
    print("\n📋 Package Contents Verification:")
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        file_list = zipf.namelist()
        print(f"   Total files in package: {len(file_list)}")
        
        # Check for critical files
        critical_checks = {
            'LangChain Integration': 'agents/langchain_flow.py' in file_list,
            'Enhanced Retrieval': 'retrieval/index.py' in file_list, 
            'Memory Manager': 'agents/memory.py' in file_list,
            'Configuration': 'config.yaml' in file_list,
            'Environment Setup': '.env.example' in file_list,
            'Logs (≥5 entries)': 'logs/run.jsonl' in file_list,
            'Red Team Results': 'eval/redteam_results.json' in file_list,
            'Dependencies': 'requirements.txt' in file_list,
        }
        
        for check_name, passed in critical_checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
    
    # Additional verification
    print("\n🔍 Additional Verification:")
    
    # Check logs file size and entry count  
    if os.path.exists('logs/run.jsonl'):
        with open('logs/run.jsonl', 'r') as f:
            log_entries = len(f.readlines())
        print(f"   📊 Log entries: {log_entries} (required: ≥5)")
        
    # Check config.yaml for LangChain backend
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            config_content = f.read()
            has_langchain = 'langchain' in config_content.lower()
        print(f"   🔧 LangChain config: {'✅' if has_langchain else '❌'}")
    
    # Check requirements for LangChain packages
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            reqs = f.read().lower()
            has_langchain = 'langchain' in reqs and 'llama-index' in reqs
        print(f"   📦 LangChain dependencies: {'✅' if has_langchain else '❌'}")
    
    print(f"\n🎯 Ready for submission: {zip_filename}")
    return True

if __name__ == "__main__":
    success = create_submission_package()
    if not success:
        print("\n⚠️  Please resolve missing files before submission!")
        exit(1)
    else:
        print("\n🚀 Submission package ready for upload!")