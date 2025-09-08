"""
ZenGlow OCR Table Extraction Module

This module implements table/figure extraction heuristics for OCR text processing.
It detects table-like structures from OCR text and exports them as structured data.

Features:
- Heuristic detection of consistent whitespace columns
- Tabular delimiter detection (pipes, tabs, multiple spaces)
- Export to CSV and Markdown formats
- Manifest generation for tracking table artifacts
- Graceful handling when no tables are detected
"""

import re
import csv
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TableDetectionResult:
    """Result of table detection on a text block."""
    is_table: bool
    confidence: float
    rows: List[List[str]]
    headers: Optional[List[str]] = None
    delimiter_type: str = "whitespace"
    start_line: int = 0
    end_line: int = 0


class TableExtractor:
    """
    Extracts table-like structures from OCR text using heuristic detection.
    
    Detection methods:
    1. Consistent whitespace column alignment
    2. Delimiter-based tables (pipes, tabs, commas)
    3. Header detection based on formatting patterns
    """
    
    def __init__(self, 
                 min_columns: int = 2,
                 min_rows: int = 2,
                 min_confidence: float = 0.6):
        """
        Initialize the table extractor.
        
        Args:
            min_columns: Minimum number of columns to consider as table
            min_rows: Minimum number of rows to consider as table
            min_confidence: Minimum confidence threshold for table detection
        """
        self.min_columns = min_columns
        self.min_rows = min_rows
        self.min_confidence = min_confidence
    
    def extract_tables_from_text(self, text: str, page_num: int = 0) -> List[TableDetectionResult]:
        """
        Extract all tables from OCR text.
        
        Args:
            text: OCR text to analyze
            page_num: Page number for tracking
            
        Returns:
            List of detected tables
        """
        if not text or not text.strip():
            return []
        
        lines = text.split('\n')
        tables = []
        
        # Try different detection methods
        tables.extend(self._detect_delimiter_tables(lines))
        tables.extend(self._detect_whitespace_tables(lines))
        
        # Filter by confidence and minimum requirements
        filtered_tables = []
        for table in tables:
            if (table.confidence >= self.min_confidence and 
                len(table.rows) >= self.min_rows and
                all(len(row) >= self.min_columns for row in table.rows)):
                filtered_tables.append(table)
        
        return filtered_tables
    
    def _detect_delimiter_tables(self, lines: List[str]) -> List[TableDetectionResult]:
        """Detect tables with explicit delimiters (|, \t, multiple spaces)."""
        tables = []
        
        # Check for pipe-delimited tables
        tables.extend(self._detect_pipe_tables(lines))
        
        # Check for tab-delimited tables
        tables.extend(self._detect_tab_tables(lines))
        
        return tables
    
    def _detect_pipe_tables(self, lines: List[str]) -> List[TableDetectionResult]:
        """Detect pipe-delimited tables (|col1|col2|col3|)."""
        tables = []
        table_start = None
        table_rows = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for lines with multiple pipes
            if '|' in line and line.count('|') >= 2:
                # Skip markdown separator lines (e.g., |----|----|)
                if self._is_markdown_separator(line):
                    continue
                    
                # Parse pipe-delimited row
                cells = [cell.strip() for cell in line.split('|')]
                # Remove empty cells from start/end (common in markdown tables)
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]
                
                if len(cells) >= self.min_columns:
                    if table_start is None:
                        table_start = i
                    table_rows.append(cells)
                else:
                    # End current table if we have one
                    if table_rows:
                        tables.append(self._create_table_result(
                            table_rows, table_start, i-1, "pipe", lines
                        ))
                        table_rows = []
                        table_start = None
            else:
                # End current table
                if table_rows:
                    tables.append(self._create_table_result(
                        table_rows, table_start, i-1, "pipe", lines
                    ))
                    table_rows = []
                    table_start = None
        
        # Handle table at end of text
        if table_rows:
            tables.append(self._create_table_result(
                table_rows, table_start, len(lines)-1, "pipe", lines
            ))
        
        return tables
    
    def _detect_tab_tables(self, lines: List[str]) -> List[TableDetectionResult]:
        """Detect tab-delimited tables."""
        tables = []
        table_start = None
        table_rows = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for lines with tabs
            if '\t' in line:
                cells = [cell.strip() for cell in line.split('\t')]
                cells = [cell for cell in cells if cell]  # Remove empty cells
                
                if len(cells) >= self.min_columns:
                    if table_start is None:
                        table_start = i
                    table_rows.append(cells)
                else:
                    # End current table
                    if table_rows:
                        tables.append(self._create_table_result(
                            table_rows, table_start, i-1, "tab", lines
                        ))
                        table_rows = []
                        table_start = None
            else:
                # End current table
                if table_rows:
                    tables.append(self._create_table_result(
                        table_rows, table_start, i-1, "tab", lines
                    ))
                    table_rows = []
                    table_start = None
        
        # Handle table at end of text
        if table_rows:
            tables.append(self._create_table_result(
                table_rows, table_start, len(lines)-1, "tab", lines
            ))
        
        return tables
    
    def _detect_whitespace_tables(self, lines: List[str]) -> List[TableDetectionResult]:
        """Detect tables with consistent whitespace column alignment."""
        tables = []
        
        # Look for consistent column patterns
        potential_tables = self._find_aligned_text_blocks(lines)
        
        for block_start, block_end, block_lines in potential_tables:
            table_data = self._parse_whitespace_table(block_lines)
            if table_data:
                confidence = self._calculate_whitespace_confidence(table_data)
                if confidence >= self.min_confidence:
                    result = TableDetectionResult(
                        is_table=True,
                        confidence=confidence,
                        rows=table_data,
                        delimiter_type="whitespace",
                        start_line=block_start,
                        end_line=block_end
                    )
                    # Try to detect headers
                    result.headers = self._detect_headers(table_data, block_lines)
                    tables.append(result)
        
        return tables
    
    def _find_aligned_text_blocks(self, lines: List[str]) -> List[Tuple[int, int, List[str]]]:
        """Find blocks of text that might be aligned tables."""
        blocks = []
        current_block = []
        block_start = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines or lines that are clearly not tabular
            if not line or len(line.split()) < self.min_columns:
                if current_block and len(current_block) >= self.min_rows:
                    blocks.append((block_start, i-1, current_block))
                current_block = []
                block_start = None
                continue
            
            # Check if line has potential for being part of a table
            if self._line_looks_tabular(line):
                if block_start is None:
                    block_start = i
                current_block.append(line)
            else:
                if current_block and len(current_block) >= self.min_rows:
                    blocks.append((block_start, i-1, current_block))
                current_block = []
                block_start = None
        
        # Handle block at end
        if current_block and len(current_block) >= self.min_rows:
            blocks.append((block_start, len(lines)-1, current_block))
        
        return blocks
    
    def _line_looks_tabular(self, line: str) -> bool:
        """Check if a line looks like it could be part of a table."""
        # Has multiple words with reasonable spacing
        words = line.split()
        if len(words) < self.min_columns:
            return False
        
        # Check for consistent spacing patterns
        spaces_between_words = []
        words_positions = []
        start = 0
        for word in words:
            pos = line.find(word, start)
            words_positions.append(pos)
            if len(words_positions) > 1:
                spaces_between_words.append(pos - words_positions[-2] - len(words[len(words_positions)-2]))
            start = pos + len(word)
        
        # Look for patterns in spacing
        if spaces_between_words:
            avg_spacing = sum(spaces_between_words) / len(spaces_between_words)
            # Reasonable spacing suggests tabular structure
            return avg_spacing >= 2
        
        return True
    
    def _parse_whitespace_table(self, lines: List[str]) -> Optional[List[List[str]]]:
        """Parse whitespace-aligned table into structured data."""
        if not lines:
            return None
        
        # Determine column boundaries by analyzing character positions
        column_boundaries = self._detect_column_boundaries(lines)
        if len(column_boundaries) < self.min_columns + 1:
            return None
        
        # Extract data using column boundaries
        table_data = []
        for line in lines:
            row = []
            for i in range(len(column_boundaries) - 1):
                start = column_boundaries[i]
                end = column_boundaries[i + 1]
                cell = line[start:end].strip() if end <= len(line) else line[start:].strip()
                row.append(cell)
            
            # Only add rows with actual content
            if any(cell for cell in row):
                table_data.append(row)
        
        return table_data if len(table_data) >= self.min_rows else None
    
    def _detect_column_boundaries(self, lines: List[str]) -> List[int]:
        """Detect column boundaries by analyzing whitespace patterns."""
        if not lines:
            return []
        
        max_length = max(len(line) for line in lines)
        char_frequency = [0] * max_length
        
        # Count non-space characters at each position
        for line in lines:
            for i, char in enumerate(line):
                if char != ' ' and char != '\t':
                    char_frequency[i] += 1
        
        # Find column boundaries (positions where few lines have characters)
        boundaries = [0]
        threshold = len(lines) * 0.3  # At least 30% of lines should have content
        
        in_column = False
        for i, freq in enumerate(char_frequency):
            if freq >= threshold:
                if not in_column:
                    # Start of a column
                    in_column = True
            else:
                if in_column:
                    # End of a column
                    boundaries.append(i)
                    in_column = False
        
        # Add final boundary
        if in_column:
            boundaries.append(max_length)
        
        return boundaries
    
    def _calculate_whitespace_confidence(self, table_data: List[List[str]]) -> float:
        """Calculate confidence score for whitespace-detected table."""
        if not table_data:
            return 0.0
        
        score = 0.0
        
        # Consistent number of columns
        col_counts = [len(row) for row in table_data]
        if col_counts:
            most_common_cols = max(set(col_counts), key=col_counts.count)
            consistency = col_counts.count(most_common_cols) / len(col_counts)
            score += 0.4 * consistency
        
        # Data type consistency within columns
        if table_data:
            num_cols = len(table_data[0])
            for col_idx in range(num_cols):
                column_data = [row[col_idx] for row in table_data if col_idx < len(row)]
                column_data = [cell for cell in column_data if cell.strip()]
                
                if column_data:
                    # Check for numeric consistency
                    numeric_count = sum(1 for cell in column_data if self._is_numeric(cell))
                    numeric_ratio = numeric_count / len(column_data)
                    
                    # Reward columns that are consistently numeric or consistently text
                    if numeric_ratio > 0.8 or numeric_ratio < 0.2:
                        score += 0.1
        
        # Table size bonus
        size_score = min(0.3, len(table_data) * 0.05)
        score += size_score
        
        return min(1.0, score)
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text represents a number."""
        try:
            float(text.replace(',', '').replace('$', '').replace('%', ''))
            return True
        except ValueError:
            return False
    
    def _is_markdown_separator(self, line: str) -> bool:
        """Check if line is a markdown table separator (e.g., |----|----|)."""
        line = line.strip()
        if not line.startswith('|') or not line.endswith('|'):
            return False
        
        # Remove pipes and check if remaining characters are mostly dashes or spaces
        content = line[1:-1]
        cells = content.split('|')
        
        for cell in cells:
            cell = cell.strip()
            # Check if cell contains only dashes, spaces, and colons (for alignment)
            if cell and not re.match(r'^[-:\s]+$', cell):
                return False
        
        return True
    
    def _detect_headers(self, table_data: List[List[str]], original_lines: List[str]) -> Optional[List[str]]:
        """Try to detect table headers."""
        if not table_data:
            return None
        
        # Simple heuristic: first row is likely headers if it's mostly text
        # and subsequent rows have more numbers
        first_row = table_data[0]
        
        if len(table_data) < 2:
            return first_row
        
        # Check if first row is more text-heavy than subsequent rows
        first_row_numeric = sum(1 for cell in first_row if self._is_numeric(cell))
        first_row_text_ratio = 1 - (first_row_numeric / len(first_row))
        
        # Check average numeric ratio in other rows
        other_rows_numeric = 0
        other_rows_total = 0
        for row in table_data[1:3]:  # Check first few data rows
            for cell in row:
                if cell.strip():
                    other_rows_total += 1
                    if self._is_numeric(cell):
                        other_rows_numeric += 1
        
        if other_rows_total > 0:
            other_rows_numeric_ratio = other_rows_numeric / other_rows_total
            
            # If first row is more text and others are more numeric, first row is likely headers
            if first_row_text_ratio > 0.6 and other_rows_numeric_ratio > 0.4:
                return first_row
        
        return None
    
    def _create_table_result(self, rows: List[List[str]], start_line: int, 
                           end_line: int, delimiter_type: str, original_lines: List[str]) -> TableDetectionResult:
        """Create a TableDetectionResult from parsed rows."""
        confidence = 0.8 if delimiter_type in ["pipe", "tab"] else 0.6
        
        result = TableDetectionResult(
            is_table=True,
            confidence=confidence,
            rows=rows,
            delimiter_type=delimiter_type,
            start_line=start_line,
            end_line=end_line
        )
        
        # Try to detect headers
        result.headers = self._detect_headers(rows, original_lines[start_line:end_line+1])
        
        return result
    
    def export_table_to_csv(self, table: TableDetectionResult, output_path: str) -> bool:
        """
        Export detected table to CSV format.
        
        Args:
            table: Detected table data
            output_path: Path to save CSV file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers if detected
                if table.headers:
                    writer.writerow(table.headers)
                    # Write data rows (skip first if it was headers)
                    data_rows = table.rows[1:] if table.headers else table.rows
                else:
                    data_rows = table.rows
                
                # Write data rows
                for row in data_rows:
                    writer.writerow(row)
            
            return True
        except Exception as e:
            print(f"Error exporting table to CSV: {e}")
            return False
    
    def export_table_to_markdown(self, table: TableDetectionResult, output_path: str) -> bool:
        """
        Export detected table to Markdown format.
        
        Args:
            table: Detected table data
            output_path: Path to save Markdown file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as mdfile:
                if table.headers:
                    # Write headers
                    mdfile.write("| " + " | ".join(table.headers) + " |\n")
                    mdfile.write("| " + " | ".join(["---"] * len(table.headers)) + " |\n")
                    # Write data rows (skip first if it was headers)
                    data_rows = table.rows[1:] if table.headers else table.rows
                else:
                    data_rows = table.rows
                
                # Write data rows
                for row in data_rows:
                    mdfile.write("| " + " | ".join(row) + " |\n")
            
            return True
        except Exception as e:
            print(f"Error exporting table to Markdown: {e}")
            return False


class TableExtractionManifest:
    """Manages manifest of extracted table artifacts."""
    
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.manifest_data = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create new one."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return {
            "version": "1.0",
            "created": None,
            "updated": None,
            "tables": []
        }
    
    def add_table_artifact(self, page_num: int, table_index: int, 
                          csv_path: str, md_path: str, 
                          table_info: TableDetectionResult) -> None:
        """Add a table artifact to the manifest."""
        from datetime import datetime
        
        now = datetime.now().isoformat()
        
        if self.manifest_data["created"] is None:
            self.manifest_data["created"] = now
        self.manifest_data["updated"] = now
        
        artifact = {
            "id": f"page_{page_num}_table_{table_index}",
            "page": page_num,
            "table_index": table_index,
            "csv_path": csv_path,
            "md_path": md_path,
            "confidence": table_info.confidence,
            "delimiter_type": table_info.delimiter_type,
            "rows": len(table_info.rows),
            "columns": len(table_info.rows[0]) if table_info.rows else 0,
            "has_headers": table_info.headers is not None,
            "start_line": table_info.start_line,
            "end_line": table_info.end_line
        }
        
        self.manifest_data["tables"].append(artifact)
    
    def save_manifest(self) -> bool:
        """Save manifest to file."""
        try:
            os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving manifest: {e}")
            return False
    
    def get_table_paths(self) -> List[str]:
        """Get list of all table artifact paths."""
        paths = []
        for table in self.manifest_data.get("tables", []):
            paths.extend([table.get("csv_path"), table.get("md_path")])
        return [path for path in paths if path]


def process_ocr_text(text: str, output_dir: str, page_num: int = 0) -> Dict[str, Any]:
    """
    Main function to process OCR text and extract tables.
    
    Args:
        text: OCR text to process
        output_dir: Directory to save extracted tables
        page_num: Page number for file naming
        
    Returns:
        Dictionary with processing results
    """
    # Initialize extractor
    extractor = TableExtractor()
    
    # Initialize manifest
    manifest_path = os.path.join(output_dir, "table_manifest.json")
    manifest = TableExtractionManifest(manifest_path)
    
    # Extract tables
    tables = extractor.extract_tables_from_text(text, page_num)
    
    results = {
        "page": page_num,
        "tables_found": len(tables),
        "tables": [],
        "manifest_path": manifest_path
    }
    
    # Export each table
    for i, table in enumerate(tables):
        # Generate file paths
        csv_filename = f"page_{page_num}_table_{i}.csv"
        md_filename = f"page_{page_num}_table_{i}.md"
        csv_path = os.path.join(output_dir, csv_filename)
        md_path = os.path.join(output_dir, md_filename)
        
        # Export files
        csv_success = extractor.export_table_to_csv(table, csv_path)
        md_success = extractor.export_table_to_markdown(table, md_path)
        
        if csv_success and md_success:
            # Add to manifest
            manifest.add_table_artifact(page_num, i, csv_path, md_path, table)
            
            results["tables"].append({
                "index": i,
                "csv_path": csv_path,
                "md_path": md_path,
                "confidence": table.confidence,
                "rows": len(table.rows),
                "columns": len(table.rows[0]) if table.rows else 0,
                "delimiter_type": table.delimiter_type
            })
    
    # Save manifest
    manifest.save_manifest()
    
    return results


if __name__ == "__main__":
    # Example usage
    sample_text = """
Product Sales Report Q1 2024

Item Name       | Quantity | Price | Total
----------------|----------|-------|--------
Widget A        | 150      | $25   | $3,750
Widget B        | 200      | $30   | $6,000
Widget C        | 75       | $45   | $3,375
----------------|----------|-------|--------
Total           | 425      |       | $13,125

Summary:
- Best seller: Widget B
- Lowest performer: Widget C
"""
    
    # Process sample text
    result = process_ocr_text(sample_text, "/tmp/ocr_output", page_num=1)
    print(f"Processing complete: {result}")