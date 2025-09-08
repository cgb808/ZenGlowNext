# OCR Table Extraction Module

This module implements table/figure extraction heuristics for OCR text processing as part of the ZenGlow AI data processing pipeline.

## Features

- **Heuristic Table Detection**: Detects consistent whitespace columns and tabular delimiters
- **Multiple Format Support**: Handles pipe-delimited (`|`), tab-delimited, and whitespace-aligned tables
- **Export Formats**: Exports to CSV and Markdown formats
- **Manifest Generation**: Creates JSON manifest linking table artifacts
- **Graceful Handling**: No-op when no tables detected

## Quick Start

```python
from table_extractor import process_ocr_text

# Process OCR text and extract tables
result = process_ocr_text(ocr_text, output_dir="/path/to/output", page_num=1)

print(f"Found {result['tables_found']} tables")
for table in result['tables']:
    print(f"CSV: {table['csv_path']}")
    print(f"MD: {table['md_path']}")
```

## Usage Examples

### Basic Usage

```python
from table_extractor import TableExtractor

extractor = TableExtractor()
tables = extractor.extract_tables_from_text(ocr_text)

for table in tables:
    print(f"Confidence: {table.confidence}")
    print(f"Rows: {len(table.rows)}")
    print(f"Type: {table.delimiter_type}")
```

### Export Tables

```python
# Export to CSV
extractor.export_table_to_csv(table, "output/table.csv")

# Export to Markdown
extractor.export_table_to_markdown(table, "output/table.md")
```

### Manifest Management

```python
from table_extractor import TableExtractionManifest

manifest = TableExtractionManifest("manifest.json")
manifest.add_table_artifact(page_num=1, table_index=0, 
                           csv_path="table.csv", md_path="table.md", 
                           table_info=table)
manifest.save_manifest()
```

## Supported Table Formats

### 1. Pipe-Delimited Tables

```
| Product | Quantity | Price |
|---------|----------|-------|
| Widget A| 150      | $25   |
| Widget B| 200      | $30   |
```

### 2. Tab-Delimited Tables

```
Name	Age	City
John	25	New York
Jane	30	Los Angeles
```

### 3. Whitespace-Aligned Tables

```
Product      Quantity    Price    Total
Widget A     150         $25      $3,750
Widget B     200         $30      $6,000
```

## Configuration

The `TableExtractor` class accepts these parameters:

- `min_columns` (default: 2): Minimum columns required for table detection
- `min_rows` (default: 2): Minimum rows required for table detection  
- `min_confidence` (default: 0.6): Minimum confidence threshold

```python
extractor = TableExtractor(min_columns=3, min_rows=3, min_confidence=0.7)
```

## Output Files

For each detected table, the following files are generated:

- `page_{N}_table_{M}.csv`: CSV format of the table
- `page_{N}_table_{M}.md`: Markdown format of the table
- `table_manifest.json`: JSON manifest with metadata

## Manifest Format

```json
{
  "version": "1.0",
  "created": "2024-01-01T00:00:00",
  "updated": "2024-01-01T00:00:00",
  "tables": [
    {
      "id": "page_1_table_0",
      "page": 1,
      "table_index": 0,
      "csv_path": "/path/to/table.csv",
      "md_path": "/path/to/table.md",
      "confidence": 0.8,
      "delimiter_type": "pipe",
      "rows": 4,
      "columns": 3,
      "has_headers": true,
      "start_line": 2,
      "end_line": 5
    }
  ]
}
```

## Testing

Run the test suite:

```bash
python test_table_extractor.py
```

Run the demo with sample data:

```bash
python demo_ocr_extraction.py
```

## Acceptance Criteria ✅

This implementation meets all the specified acceptance criteria:

1. **✅ At least one sample with a simple table yields a table artifact file**
   - The simple table sample generates both CSV and MD files

2. **✅ Manifest includes { tables: [paths] } when detected**
   - The manifest.json includes table paths and metadata

3. **✅ Graceful no-op when none detected**
   - Files with no tables are processed without errors, creating an empty manifest

## Integration with ZenGlow

This module integrates with the ZenGlow AI data processing pipeline:

- Place OCR text processing calls in data ingestion workflows
- Use manifest data for tracking extracted artifacts
- Export tables for further analysis in the clustering pipeline
- Connect to dashboard visualization for table preview

## Dependencies

All dependencies are built-in Python modules:
- `json` - for manifest files
- `csv` - for CSV export
- `re` - for pattern matching
- `os`, `pathlib` - for file operations
- `dataclasses` - for result structures

No additional packages need to be installed.