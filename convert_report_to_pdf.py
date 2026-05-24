#!/usr/bin/env python3
"""
PDF Report Generator
Converts Technical_Report.md to PDF format using available tools
"""

import os
import subprocess
import sys

def convert_to_pdf():
    """Convert Technical_Report.md to PDF using pandoc or alternative methods"""
    
    input_file = "Technical_Report.md"
    output_file = "Technical_Report.pdf"
    
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found!")
        return False
    
    print(f"🔄 Converting {input_file} to {output_file}...")
    
    # Method 1: Try pandoc (most reliable)
    try:
        result = subprocess.run([
            'pandoc', input_file, 
            '-o', output_file,
            '--pdf-engine=xelatex',
            '--variable', 'geometry:margin=1in',
            '--toc',
            '--number-sections'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ PDF created successfully: {output_file}")
            return True
        else:
            print(f"⚠️ Pandoc failed: {result.stderr}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️ Pandoc not available, trying alternative methods...")
    
    # Method 2: Try markdown-pdf (npm package)
    try:
        result = subprocess.run([
            'markdown-pdf', input_file,
            '-o', output_file
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ PDF created successfully: {output_file}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️ markdown-pdf not available...")
    
    # Method 3: Provide manual instructions
    print("\n📋 Manual PDF Creation Instructions:")
    print("=" * 50)
    print("Since automated PDF conversion is not available, please:")
    print("1. Open Technical_Report.md in any Markdown editor")
    print("2. Export/Print to PDF using browser or editor")
    print("3. Recommended tools:")
    print("   - VS Code: Install 'Markdown PDF' extension")
    print("   - Browser: Open MD file and print to PDF")
    print("   - Online: Use markdowntopdf.com")
    print("   - Pandoc: Install pandoc and run conversion")
    
    print(f"\n📄 Report contains:")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = len(content.split('\n'))
        words = len(content.split())
        chars = len(content)
    
    print(f"   - {lines:,} lines")
    print(f"   - {words:,} words")  
    print(f"   - {chars:,} characters")
    print("   - Comprehensive LangChain + LlamaIndex analysis")
    print("   - Architecture diagrams and implementation details")
    print("   - Security analysis and test results")
    print("   - Limitations and ethical considerations")
    
    return False

if __name__ == "__main__":
    success = convert_to_pdf()
    if not success:
        print("\n💡 The Markdown report is complete and ready for manual PDF conversion.")
        sys.exit(0)  # Not an error - just need manual conversion