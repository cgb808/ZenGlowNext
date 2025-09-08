#!/usr/bin/env python3
"""
Demo script for OCR Table Extraction

This script demonstrates the table extraction functionality using the sample data files.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path so we can import our module
sys.path.append(os.path.dirname(__file__))

from table_extractor import process_ocr_text


def demo_table_extraction():
    """Demonstrate table extraction with sample files."""
    
    sample_dir = Path(__file__).parent / "sample_data"
    output_dir = Path("/tmp/demo_ocr_output")
    output_dir.mkdir(exist_ok=True)
    
    sample_files = [
        "sample_simple_table.txt",
        "sample_complex_table.txt", 
        "sample_whitespace_table.txt",
        "sample_no_tables.txt"
    ]
    
    print("🔍 ZenGlow OCR Table Extraction Demo")
    print("=" * 50)
    
    for i, filename in enumerate(sample_files):
        file_path = sample_dir / filename
        
        if not file_path.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        print(f"\n📄 Processing: {filename}")
        print("-" * 30)
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Process the text
        result = process_ocr_text(text, str(output_dir), page_num=i)
        
        # Display results
        print(f"Page {result['page']}: {result['tables_found']} table(s) found")
        
        if result['tables_found'] > 0:
            for j, table in enumerate(result['tables']):
                print(f"  Table {j+1}:")
                print(f"    Confidence: {table['confidence']:.2f}")
                print(f"    Rows: {table['rows']}, Columns: {table['columns']}")
                print(f"    Type: {table['delimiter_type']}")
                print(f"    CSV: {os.path.basename(table['csv_path'])}")
                print(f"    MD: {os.path.basename(table['md_path'])}")
        else:
            print("  ✅ No tables detected (graceful no-op)")
    
    # Show manifest summary
    manifest_path = output_dir / "table_manifest.json"
    if manifest_path.exists():
        print(f"\n📋 Manifest created: {manifest_path}")
        
        import json
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        print(f"   Total tables extracted: {len(manifest['tables'])}")
        print(f"   Created: {manifest.get('created', 'N/A')}")
        print(f"   Updated: {manifest.get('updated', 'N/A')}")
    
    print(f"\n📁 Output directory: {output_dir}")
    print(f"   Files created: {len(list(output_dir.glob('*')))}")
    
    # List all created files
    print("\n📋 Generated Files:")
    for file_path in sorted(output_dir.glob('*')):
        print(f"   {file_path.name}")
    
    print("\n✅ Demo completed successfully!")
    
    return output_dir


if __name__ == "__main__":
    demo_table_extraction()