#!/usr/bin/env python3
"""
The Stack Smol Processor for ZenGlow
Processes programming language datasets from HuggingFace "the-stack-smol" dataset
with quality-based filtering and weighted scoring for professional reference data
"""
from datasets import load_dataset, Dataset
import pandas as pd
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import statistics

# Configuration - 30 programming languages in the-stack-smol
LANGUAGES = [
    "assembly",
    "batchfile",
    "c++",
    "c",
    "c-sharp",
    "cmake",
    "css",
    "dockerfile",
    "fortran",
    "go",
    "haskell",
    "html",
    "java",
    "javascript",
    "julia",
    "lua",
    "makefile",
    "markdown",
    "perl",
    "php",
    "powershell",
    "python",
    "ruby",
    "rust",
    "scala",
    "shell",
    "sql",
    "tex",
    "typescript",
    "visual-basic",
]

DEFAULT_SEED = 0
DEFAULT_SIZE = 10_000  # Each language has exactly 10k samples in the-stack-smol
OUTPUT_BASE_DIR = "./data_sources/professional_reference/the_stack_smol"

# Quality thresholds for code filtering
QUALITY_THRESHOLDS = {
    "min_alphanum_fraction": 0.5,  # At least 50% alphanumeric (code vs comments)
    "max_avg_line_length": 120,  # Reasonable line length
    "max_max_line_length": 500,  # No extremely long lines
    "min_size": 50,  # Minimum file size (bytes)
    "max_size": 50000,  # Maximum file size (avoid huge files)
    "preferred_licenses": [  # Safe licenses for usage
        "MIT",
        "Apache-2.0",
        "BSD-3-Clause",
        "BSD-2-Clause",
        "ISC",
        "Unlicense",
        "CC0-1.0",
    ],
}


def calculate_quality_score(sample: Dict[str, Any]) -> float:
    """
    Calculate a quality score (0-1) based on code metrics
    Higher scores indicate better code quality for ZenGlow
    """
    score = 0.0
    factors = 0

    # Alphanumeric fraction (0.5 = good balance of code vs comments)
    if "alphanum_fraction" in sample and sample["alphanum_fraction"] is not None:
        alphanum = float(sample["alphanum_fraction"])
        # Optimal range: 0.6-0.8 (good code with some comments)
        if 0.6 <= alphanum <= 0.8:
            score += 1.0
        elif 0.5 <= alphanum < 0.6 or 0.8 < alphanum <= 0.9:
            score += 0.7
        elif alphanum >= 0.5:
            score += 0.3
        factors += 1

    # Average line length (readability factor)
    if "avg_line_length" in sample and sample["avg_line_length"] is not None:
        avg_len = float(sample["avg_line_length"])
        # Optimal range: 40-80 characters
        if 40 <= avg_len <= 80:
            score += 1.0
        elif 30 <= avg_len < 40 or 80 < avg_len <= 100:
            score += 0.7
        elif 20 <= avg_len < 30 or 100 < avg_len <= 120:
            score += 0.4
        else:
            score += 0.1
        factors += 1

    # File size (complexity indicator)
    if "size" in sample and sample["size"] is not None:
        size = int(sample["size"])
        # Optimal range: 500-5000 bytes (substantial but not overwhelming)
        if 500 <= size <= 5000:
            score += 1.0
        elif 200 <= size < 500 or 5000 < size <= 15000:
            score += 0.7
        elif 100 <= size < 200 or 15000 < size <= 30000:
            score += 0.4
        else:
            score += 0.1
        factors += 1

    # License quality (prefer permissive licenses)
    if "licenses" in sample and sample["licenses"]:
        licenses = (
            sample["licenses"]
            if isinstance(sample["licenses"], list)
            else [sample["licenses"]]
        )
        has_good_license = any(
            lic in QUALITY_THRESHOLDS["preferred_licenses"] for lic in licenses if lic
        )
        if has_good_license:
            score += 1.0
        else:
            score += 0.5  # Still usable, but less preferred
        factors += 1

    return score / factors if factors > 0 else 0.5


def filter_by_quality(
    dataset, min_quality_score: float = 0.6, apply_thresholds: bool = True
) -> tuple:
    """
    Filter dataset by quality metrics and return filtered dataset with stats
    """
    if len(dataset) == 0:
        return dataset, {"total": 0, "filtered": 0, "quality_stats": {}}

    original_count = len(dataset)
    indices_to_keep = []
    quality_scores = []

    for i in range(len(dataset)):
        sample = dataset[i]

        # Apply hard thresholds first
        if apply_thresholds:
            # Check alphanum fraction
            if (
                "alphanum_fraction" in sample
                and sample["alphanum_fraction"] is not None
            ):
                if (
                    float(sample["alphanum_fraction"])
                    < QUALITY_THRESHOLDS["min_alphanum_fraction"]
                ):
                    continue

            # Check line lengths
            if "avg_line_length" in sample and sample["avg_line_length"] is not None:
                if (
                    float(sample["avg_line_length"])
                    > QUALITY_THRESHOLDS["max_avg_line_length"]
                ):
                    continue

            if "max_line_length" in sample and sample["max_line_length"] is not None:
                if (
                    float(sample["max_line_length"])
                    > QUALITY_THRESHOLDS["max_max_line_length"]
                ):
                    continue

            # Check file size
            if "size" in sample and sample["size"] is not None:
                size = int(sample["size"])
                if (
                    size < QUALITY_THRESHOLDS["min_size"]
                    or size > QUALITY_THRESHOLDS["max_size"]
                ):
                    continue

        # Calculate quality score
        quality_score = calculate_quality_score(sample)

        if quality_score >= min_quality_score:
            indices_to_keep.append(i)
            quality_scores.append(quality_score)

    # Create filtered dataset
    filtered_dataset = (
        dataset.select(indices_to_keep) if indices_to_keep else dataset.select([])
    )

    # Calculate stats
    stats = {
        "total": original_count,
        "filtered": len(filtered_dataset),
        "filter_ratio": (
            len(filtered_dataset) / original_count if original_count > 0 else 0
        ),
        "quality_stats": {
            "mean_score": statistics.mean(quality_scores) if quality_scores else 0,
            "median_score": statistics.median(quality_scores) if quality_scores else 0,
            "min_score": min(quality_scores) if quality_scores else 0,
            "max_score": max(quality_scores) if quality_scores else 0,
        },
    }

    return filtered_dataset, stats


def process_the_stack_language(
    language: str,
    size: Optional[int] = None,
    seed: int = DEFAULT_SEED,
    output_dir: Optional[str] = None,
    sample_subset: bool = True,
    apply_quality_filter: bool = True,
    min_quality_score: float = 0.6,
) -> bool:
    """
    Process a single language from the-stack-smol dataset

    Args:
        language: Programming language to process
        size: Number of samples to extract (None = all 10k samples)
        seed: Random seed for reproducibility
        output_dir: Output directory (defaults to ZenGlow structure)
        sample_subset: Whether to sample a subset or use all data

    Returns:
        bool: Success status
    """
    if output_dir is None:
        output_dir = OUTPUT_BASE_DIR

    try:
        print(f"🔄 Loading {language} dataset from the-stack-smol...")

        # Load specific language dataset (each has exactly 10k samples)
        dataset = load_dataset(
            "bigcode/the-stack-smol", data_dir=f"data/{language}", split="train"
        )
        print(f"✅ Dataset {language} loaded: {len(dataset)} samples")

        # Sample subset if requested
        if sample_subset and size and size < len(dataset):
            dataset = dataset.shuffle(seed=seed).select(range(size))
            print(f"📊 Sampled {size} examples from {language}")
        else:
            size = len(dataset)
            print(f"📊 Using full dataset: {size} samples")

        # Apply quality filtering if requested
        if apply_quality_filter and len(dataset) > 0:
            print(f"🔍 Applying quality filtering (min_score: {min_quality_score})...")
            dataset, filter_stats = filter_by_quality(dataset, min_quality_score)
            print(f"📊 Quality filtering results:")
            print(f"   Original: {filter_stats['total']} samples")
            print(
                f"   Filtered: {filter_stats['filtered']} samples ({filter_stats['filter_ratio']:.1%} retained)"
            )
            if filter_stats["quality_stats"]["mean_score"] > 0:
                print(
                    f"   Avg quality score: {filter_stats['quality_stats']['mean_score']:.2f}"
                )
            size = len(dataset)  # Update size after filtering

        # Validation check - show dataset structure
        if len(dataset) > 0:
            sample = dataset[0]
            available_fields = list(sample.keys())
            print(f"🔍 Available fields: {available_fields}")
            print(f"🔍 Sample repository: {sample.get('repository_name', 'N/A')}")
            print(f"🔍 Sample language: {sample.get('lang', 'N/A')}")

        # Ensure output directory exists
        lang_dir = Path(output_dir) / language
        lang_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON for ZenGlow pipeline
        output_path = lang_dir / "dataset.json"
        dataset.to_json(str(output_path))
        print(f"💾 Dataset saved to {output_path}")

        # Create sidecar metadata for ZenGlow integration
        create_sidecar_metadata(output_path, language, size, seed, dataset)

        return True

    except Exception as e:
        print(f"❌ Error processing {language}: {e}")
        return False


def create_sidecar_metadata(
    data_path: Path, language: str, size: int, seed: int, dataset=None
) -> None:
    """Create sidecar metadata for ZenGlow integration"""
    sidecar_path = data_path.with_suffix(data_path.suffix + ".meta.json")

    # Extract some statistics from dataset if available
    avg_line_length = None
    avg_size = None
    sample_licenses = None

    if dataset and len(dataset) > 0:
        try:
            # Calculate averages from sample
            sample_size = min(100, len(dataset))
            sample_data = dataset.select(range(sample_size))

            if "avg_line_length" in sample_data.column_names:
                avg_line_length = sum(sample_data["avg_line_length"]) / len(sample_data)

            if "size" in sample_data.column_names:
                avg_size = sum(sample_data["size"]) / len(sample_data)

            if "licenses" in sample_data.column_names:
                # Get unique licenses from sample
                license_sets = [lic for lic in sample_data["licenses"] if lic]
                sample_licenses = list(
                    set(
                        [
                            item
                            for sublist in license_sets
                            for item in (
                                sublist if isinstance(sublist, list) else [sublist]
                            )
                        ]
                    )
                )[:5]
        except Exception as e:
            print(f"⚠️  Could not extract dataset statistics: {e}")

    metadata = {
        "author": "The Stack Smol Processor",
        "status": "processed",
        "version": "1.1",
        "priority": "medium",
        "tags": [
            "programming",
            "code-samples",
            f"lang-{language}",
            "the-stack-smol",
            "quality-filtered",
        ],
        "data_source": "bigcode/the-stack-smol",
        "language": language,
        "sample_count": size,
        "random_seed": seed,
        "dataset_features": [
            "content",
            "avg_line_length",
            "max_line_length",
            "alphanum_fraction",
            "licenses",
            "repository_name",
            "path",
            "size",
            "lang",
        ],
        # Quality metrics
        "quality_filtered": True,
        "avg_line_length": avg_line_length,
        "avg_file_size": avg_size,
        "sample_licenses": sample_licenses,
        # ZenGlow integration
        "weight_modifier": 1.2,  # Boost for quality-filtered code
        "content_type": "code_repository",
        "processing_notes": f"Extracted {size} quality-filtered samples from the-stack-smol dataset",
    }

    import json

    with open(sidecar_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"📝 Sidecar metadata created: {sidecar_path}")


def process_all_languages(
    languages: List[str] = LANGUAGES,
    size: Optional[int] = None,
    seed: int = DEFAULT_SEED,
    output_dir: Optional[str] = None,
    continue_on_error: bool = True,
) -> dict:
    """
    Process all specified languages from the-stack-smol dataset

    Returns:
        dict: Results summary with success/failure counts
    """
    results = {"success": [], "failed": [], "total": len(languages)}

    print(f"🚀 Starting the-stack-smol processing for {len(languages)} languages...")
    print(
        f"📊 Configuration: {size if size else 'full dataset'} samples per language, seed={seed}"
    )

    for i, language in enumerate(languages, 1):
        print(f"\n[{i}/{len(languages)}] Processing {language}...")

        try:
            success = process_the_stack_language(
                language=language,
                size=size,
                seed=seed,
                output_dir=output_dir,
                sample_subset=(size is not None),
            )

            if success:
                results["success"].append(language)
                print(f"✅ {language} completed successfully")
            else:
                results["failed"].append(language)
                print(f"❌ {language} failed")

        except Exception as e:
            results["failed"].append(language)
            print(f"❌ {language} failed with exception: {e}")

            if not continue_on_error:
                print("🛑 Stopping due to error (continue_on_error=False)")
                break

    # Summary
    print(f"\n📈 Processing Complete!")
    print(f"✅ Successful: {len(results['success'])} languages")
    print(f"❌ Failed: {len(results['failed'])} languages")

    if results["failed"]:
        print(f"Failed languages: {', '.join(results['failed'])}")

    return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process the-stack-smol dataset for ZenGlow with quality filtering"
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=LANGUAGES,
        help="Languages to process (default: all 30 languages)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=None,
        help="Number of samples per language (default: full dataset ~10k per language)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=OUTPUT_BASE_DIR,
        help="Output directory for processed data",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="Stop processing on first error"
    )
    parser.add_argument(
        "--single", type=str, metavar="LANGUAGE", help="Process only a single language"
    )

    # Quality filtering options
    parser.add_argument(
        "--no-quality-filter",
        action="store_true",
        help="Disable quality filtering (use all samples)",
    )
    parser.add_argument(
        "--min-quality-score",
        type=float,
        default=0.6,
        help="Minimum quality score for filtering (0.0-1.0, default: 0.6)",
    )
    parser.add_argument(
        "--show-quality-info",
        action="store_true",
        help="Show detailed quality information for samples",
    )

    args = parser.parse_args()

    # Validate quality score
    if not 0.0 <= args.min_quality_score <= 1.0:
        print("❌ min-quality-score must be between 0.0 and 1.0")
        exit(1)

    apply_quality_filter = not args.no_quality_filter

    # Process single language if specified
    if args.single:
        if args.single not in LANGUAGES:
            print(f"❌ Unknown language: {args.single}")
            print(f"Available languages: {', '.join(LANGUAGES)}")
            exit(1)

        success = process_the_stack_language(
            language=args.single,
            size=args.size,
            seed=args.seed,
            output_dir=args.output_dir,
            sample_subset=(args.size is not None),
            apply_quality_filter=apply_quality_filter,
            min_quality_score=args.min_quality_score,
        )

        if not success:
            exit(1)
        return

    # Process multiple languages (updated function call)
    print(f"🎯 Quality filtering: {'enabled' if apply_quality_filter else 'disabled'}")
    if apply_quality_filter:
        print(f"🎯 Minimum quality score: {args.min_quality_score}")

    # Since we need to update process_all_languages, let's do a simple loop here
    results = {"success": [], "failed": [], "total": len(args.languages)}

    for i, language in enumerate(args.languages, 1):
        print(f"\n[{i}/{len(args.languages)}] Processing {language}...")

        try:
            success = process_the_stack_language(
                language=language,
                size=args.size,
                seed=args.seed,
                output_dir=args.output_dir,
                sample_subset=(args.size is not None),
                apply_quality_filter=apply_quality_filter,
                min_quality_score=args.min_quality_score,
            )

            if success:
                results["success"].append(language)
                print(f"✅ {language} completed successfully")
            else:
                results["failed"].append(language)
                print(f"❌ {language} failed")

        except Exception as e:
            results["failed"].append(language)
            print(f"❌ {language} failed with exception: {e}")

            if args.stop_on_error:
                print("🛑 Stopping due to error")
                break

    # Summary
    print(f"\n📈 Processing Complete!")
    print(f"✅ Successful: {len(results['success'])} languages")
    print(f"❌ Failed: {len(results['failed'])} languages")

    if results["failed"]:
        print(f"Failed languages: {', '.join(results['failed'])}")
        exit(1)


if __name__ == "__main__":
    main()
