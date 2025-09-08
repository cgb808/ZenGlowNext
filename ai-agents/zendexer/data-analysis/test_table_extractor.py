"""
Test suite for OCR Table Extraction Module

Tests the table detection and extraction functionality for various table formats.
"""

import os
import tempfile
import shutil
import unittest
import json
from pathlib import Path

from table_extractor import (
    TableExtractor, 
    TableDetectionResult, 
    TableExtractionManifest,
    process_ocr_text
)


class TestTableExtractor(unittest.TestCase):
    """Test cases for table extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = TableExtractor()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pipe_delimited_table_detection(self):
        """Test detection of pipe-delimited tables."""
        text = """
Some intro text here.

| Product | Quantity | Price |
|---------|----------|-------|
| Widget A| 150      | $25   |
| Widget B| 200      | $30   |
| Widget C| 75       | $45   |

Some conclusion text.
"""
        
        tables = self.extractor.extract_tables_from_text(text)
        
        self.assertGreater(len(tables), 0, "Should detect at least one table")
        
        table = tables[0]
        self.assertTrue(table.is_table)
        self.assertEqual(table.delimiter_type, "pipe")
        self.assertGreaterEqual(table.confidence, 0.6)
        self.assertEqual(len(table.rows), 4)  # Header + 3 data rows
        self.assertEqual(len(table.rows[0]), 3)  # 3 columns
    
    def test_tab_delimited_table_detection(self):
        """Test detection of tab-delimited tables."""
        text = "Name\tAge\tCity\nJohn\t25\tNew York\nJane\t30\tLos Angeles\nBob\t35\tChicago"
        
        tables = self.extractor.extract_tables_from_text(text)
        
        self.assertGreater(len(tables), 0, "Should detect tab-delimited table")
        
        table = tables[0]
        self.assertEqual(table.delimiter_type, "tab")
        self.assertEqual(len(table.rows), 4)  # Header + 3 data rows
        self.assertEqual(len(table.rows[0]), 3)  # 3 columns
    
    def test_whitespace_aligned_table_detection(self):
        """Test detection of whitespace-aligned tables."""
        text = """
Product Report

Name         Qty    Price   Total
Widget A     150    25.00   3750.00
Widget B     200    30.00   6000.00
Widget C     75     45.00   3375.00

End of report.
"""
        
        tables = self.extractor.extract_tables_from_text(text)
        
        # Should detect at least one table
        self.assertGreater(len(tables), 0, "Should detect whitespace-aligned table")
        
        # Check table properties
        table = tables[0]
        self.assertTrue(table.is_table)
        self.assertEqual(table.delimiter_type, "whitespace")
        self.assertGreaterEqual(len(table.rows), 3)  # At least 3 data rows
    
    def test_no_table_detection(self):
        """Test that no tables are detected in regular text."""
        text = """
This is just regular paragraph text with no tabular structure.
It has multiple lines but they don't form any kind of table.
Each line is just normal prose without column alignment.
"""
        
        tables = self.extractor.extract_tables_from_text(text)
        
        self.assertEqual(len(tables), 0, "Should not detect tables in regular text")
    
    def test_csv_export(self):
        """Test CSV export functionality."""
        # Create a simple table
        table = TableDetectionResult(
            is_table=True,
            confidence=0.8,
            rows=[
                ["Name", "Age", "City"],
                ["John", "25", "New York"],
                ["Jane", "30", "Los Angeles"]
            ],
            headers=["Name", "Age", "City"],
            delimiter_type="pipe"
        )
        
        csv_path = os.path.join(self.temp_dir, "test_table.csv")
        success = self.extractor.export_table_to_csv(table, csv_path)
        
        self.assertTrue(success, "CSV export should succeed")
        self.assertTrue(os.path.exists(csv_path), "CSV file should be created")
        
        # Check CSV content
        with open(csv_path, 'r') as f:
            content = f.read()
            self.assertIn("Name,Age,City", content)
            self.assertIn("John,25,New York", content)
    
    def test_markdown_export(self):
        """Test Markdown export functionality."""
        # Create a simple table
        table = TableDetectionResult(
            is_table=True,
            confidence=0.8,
            rows=[
                ["Product", "Price"],
                ["Widget", "$25"],
                ["Gadget", "$30"]
            ],
            headers=["Product", "Price"],
            delimiter_type="pipe"
        )
        
        md_path = os.path.join(self.temp_dir, "test_table.md")
        success = self.extractor.export_table_to_markdown(table, md_path)
        
        self.assertTrue(success, "Markdown export should succeed")
        self.assertTrue(os.path.exists(md_path), "Markdown file should be created")
        
        # Check Markdown content
        with open(md_path, 'r') as f:
            content = f.read()
            self.assertIn("| Product | Price |", content)
            self.assertIn("| --- | --- |", content)
            self.assertIn("| Widget | $25 |", content)
    
    def test_manifest_creation(self):
        """Test manifest creation and management."""
        manifest_path = os.path.join(self.temp_dir, "manifest.json")
        manifest = TableExtractionManifest(manifest_path)
        
        # Create a sample table
        table = TableDetectionResult(
            is_table=True,
            confidence=0.9,
            rows=[["A", "B"], ["1", "2"]],
            delimiter_type="pipe",
            start_line=1,
            end_line=2
        )
        
        # Add artifact
        manifest.add_table_artifact(
            page_num=1, 
            table_index=0,
            csv_path="/path/to/table.csv",
            md_path="/path/to/table.md",
            table_info=table
        )
        
        # Save and verify
        success = manifest.save_manifest()
        self.assertTrue(success, "Manifest save should succeed")
        self.assertTrue(os.path.exists(manifest_path), "Manifest file should exist")
        
        # Check manifest content
        with open(manifest_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(len(data["tables"]), 1)
            self.assertEqual(data["tables"][0]["page"], 1)
            self.assertEqual(data["tables"][0]["confidence"], 0.9)


class TestFullProcessing(unittest.TestCase):
    """Test the complete OCR processing pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_ocr_text_with_table(self):
        """Test complete processing pipeline with sample table."""
        sample_text = """
Sales Report Q1 2024

| Product | Q1 Sales | Revenue |
|---------|----------|---------|
| Widget A| 150 units| $3,750  |
| Widget B| 200 units| $6,000  |
| Widget C| 75 units | $3,375  |

Total Revenue: $13,125
"""
        
        result = process_ocr_text(sample_text, self.temp_dir, page_num=1)
        
        # Verify results
        self.assertEqual(result["page"], 1)
        self.assertGreater(result["tables_found"], 0, "Should find at least one table")
        self.assertGreater(len(result["tables"]), 0, "Should have table entries")
        
        # Check files were created
        table_info = result["tables"][0]
        self.assertTrue(os.path.exists(table_info["csv_path"]), "CSV file should exist")
        self.assertTrue(os.path.exists(table_info["md_path"]), "Markdown file should exist")
        self.assertTrue(os.path.exists(result["manifest_path"]), "Manifest should exist")
        
        # Check manifest content
        with open(result["manifest_path"], 'r') as f:
            manifest_data = json.load(f)
            self.assertIn("tables", manifest_data)
            self.assertGreater(len(manifest_data["tables"]), 0)
    
    def test_process_ocr_text_without_table(self):
        """Test processing with no tables (graceful no-op)."""
        sample_text = """
This is just a regular document with no tables.
It has multiple paragraphs of text.
But nothing that looks like a table structure.
"""
        
        result = process_ocr_text(sample_text, self.temp_dir, page_num=1)
        
        # Verify graceful handling
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["tables_found"], 0, "Should find no tables")
        self.assertEqual(len(result["tables"]), 0, "Should have no table entries")
        
        # Manifest should still be created but empty
        self.assertTrue(os.path.exists(result["manifest_path"]), "Manifest should exist")
        with open(result["manifest_path"], 'r') as f:
            manifest_data = json.load(f)
            self.assertEqual(len(manifest_data["tables"]), 0)


class TestSampleData(unittest.TestCase):
    """Test with specific sample data to meet acceptance criteria."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_simple_table_sample(self):
        """Test with a simple table to meet acceptance criteria."""
        # Simple table that should definitely be detected
        simple_table_text = """
| Item | Count |
|------|-------|
| Apples | 10 |
| Oranges | 15 |
| Bananas | 8 |
"""
        
        result = process_ocr_text(simple_table_text, self.temp_dir, page_num=0)
        
        # Verify acceptance criteria
        self.assertGreater(result["tables_found"], 0, 
                          "At least one sample with a simple table should yield a table artifact file")
        
        # Check that table artifact files were created
        table = result["tables"][0]
        self.assertTrue(os.path.exists(table["csv_path"]), "CSV artifact should be created")
        self.assertTrue(os.path.exists(table["md_path"]), "MD artifact should be created")
        
        # Verify manifest includes tables paths
        with open(result["manifest_path"], 'r') as f:
            manifest_data = json.load(f)
            self.assertIn("tables", manifest_data, "Manifest should include tables key")
            self.assertGreater(len(manifest_data["tables"]), 0, "Manifest should list table paths")
            
            # Check that paths are included
            table_entry = manifest_data["tables"][0]
            self.assertIn("csv_path", table_entry)
            self.assertIn("md_path", table_entry)
        
        print(f"✅ Acceptance criteria met:")
        print(f"   - Table detected: {result['tables_found']} tables found")
        print(f"   - CSV created: {table['csv_path']}")
        print(f"   - MD created: {table['md_path']}")
        print(f"   - Manifest created: {result['manifest_path']}")


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)