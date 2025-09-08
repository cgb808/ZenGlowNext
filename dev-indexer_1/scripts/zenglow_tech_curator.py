#!/usr/bin/env python3
"""
ZenGlow Tech Stack Curator
Specialized processor for the-stack-smol dataset targeting ZenGlow's specific technology needs:
React/React Native, TypeScript/JavaScript, Python, Docker, Database technologies, etc.
"""
from datasets import load_dataset, Dataset
import pandas as pd
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import statistics
import json

# ZenGlow Tech Stack Configuration
ZENGLOW_TECH_STACK = {
    # Frontend & Mobile
    "javascript": {
        "priority": "critical",
        "weight_modifier": 1.4,
        "keywords": [
            "react",
            "expo",
            "react-native",
            "next.js",
            "vite",
            "node",
            "npm",
            "yarn",
        ],
        "file_patterns": [".js", ".jsx", "package.json", "expo", "react"],
        "quality_boost": 0.2,
    },
    "typescript": {
        "priority": "critical",
        "weight_modifier": 1.5,
        "keywords": [
            "react",
            "expo",
            "react-native",
            "next.js",
            "vite",
            "tsx",
            "types",
        ],
        "file_patterns": [".ts", ".tsx", "tsconfig", "types"],
        "quality_boost": 0.3,
    },
    # Backend & APIs
    "python": {
        "priority": "critical",
        "weight_modifier": 1.4,
        "keywords": [
            "fastapi",
            "uvicorn",
            "pydantic",
            "sqlalchemy",
            "redis",
            "pandas",
            "numpy",
        ],
        "file_patterns": [".py", "requirements", "pyproject", "main.py", "api"],
        "quality_boost": 0.2,
    },
    # Infrastructure & DevOps
    "dockerfile": {
        "priority": "high",
        "weight_modifier": 1.3,
        "keywords": ["python", "node", "nginx", "redis", "postgres", "alpine"],
        "file_patterns": ["Dockerfile", "docker-compose", ".dockerignore"],
        "quality_boost": 0.1,
    },
    # Configuration & Data
    "yaml": {
        "priority": "high",
        "weight_modifier": 1.2,
        "keywords": ["docker-compose", "github", "ci", "config", "deployment"],
        "file_patterns": [".yml", ".yaml", "compose", "config"],
        "quality_boost": 0.1,
    },
    # Database & Queries
    "sql": {
        "priority": "high",
        "weight_modifier": 1.3,
        "keywords": [
            "postgres",
            "timescale",
            "pgvector",
            "supabase",
            "select",
            "create",
        ],
        "file_patterns": [".sql", "migration", "schema", "query"],
        "quality_boost": 0.2,
    },
    # Markup & Documentation
    "html": {
        "priority": "medium",
        "weight_modifier": 1.1,
        "keywords": ["react", "component", "jsx", "responsive", "css"],
        "file_patterns": [".html", "index", "template"],
        "quality_boost": 0.1,
    },
    "css": {
        "priority": "medium",
        "weight_modifier": 1.1,
        "keywords": ["responsive", "mobile", "flexbox", "grid", "tailwind"],
        "file_patterns": [".css", ".scss", "style", "theme"],
        "quality_boost": 0.1,
    },
    "markdown": {
        "priority": "medium",
        "weight_modifier": 1.0,
        "keywords": ["readme", "docs", "api", "guide", "tutorial"],
        "file_patterns": [".md", "README", "docs", "guide"],
        "quality_boost": 0.0,
    },
    # Build & Package Management
    "makefile": {
        "priority": "medium",
        "weight_modifier": 1.1,
        "keywords": ["build", "docker", "deploy", "test", "install"],
        "file_patterns": ["Makefile", "makefile", "build"],
        "quality_boost": 0.1,
    },
    # Shell Scripts
    "shell": {
        "priority": "medium",
        "weight_modifier": 1.1,
        "keywords": ["docker", "deploy", "build", "setup", "install"],
        "file_patterns": [".sh", ".bash", "setup", "deploy"],
        "quality_boost": 0.1,
    },
}

# Enhanced quality thresholds for ZenGlow tech stack
ZENGLOW_QUALITY_THRESHOLDS = {
    "min_alphanum_fraction": 0.45,  # More lenient for config files
    "max_avg_line_length": 100,  # Allow slightly longer lines for modern code
    "max_max_line_length": 400,  # Allow longer lines for complex expressions
    "min_size": 30,  # Include smaller utility files
    "max_size": 100000,  # Allow larger files for comprehensive examples
    "preferred_licenses": [
        "MIT",
        "Apache-2.0",
        "BSD-3-Clause",
        "BSD-2-Clause",
        "ISC",
        "Unlicense",
        "CC0-1.0",
        "GPL-3.0",
    ],
}

OUTPUT_BASE_DIR = "./data_sources/professional_reference/zenglow_tech_stack"


def calculate_zenglow_quality_score(sample: Dict[str, Any], language: str) -> float:
    """
    Calculate ZenGlow-specific quality score with tech stack bonuses
    """
    base_score = 0.0
    factors = 0

    # Get language-specific config
    lang_config = ZENGLOW_TECH_STACK.get(language, {})
    quality_boost = lang_config.get("quality_boost", 0.0)

    # Alphanum fraction (more lenient for config files)
    if "alphanum_fraction" in sample and sample["alphanum_fraction"] is not None:
        alphanum = float(sample["alphanum_fraction"])
        if language in ["yaml", "dockerfile", "makefile"]:
            # More lenient for config files
            if alphanum >= 0.4:
                base_score += 1.0
            elif alphanum >= 0.3:
                base_score += 0.7
            else:
                base_score += 0.3
        else:
            # Standard scoring for code files
            if 0.55 <= alphanum <= 0.85:
                base_score += 1.0
            elif 0.45 <= alphanum < 0.55 or 0.85 < alphanum <= 0.95:
                base_score += 0.7
            elif alphanum >= 0.35:
                base_score += 0.4
        factors += 1

    # Line length (more lenient for modern frameworks)
    if "avg_line_length" in sample and sample["avg_line_length"] is not None:
        avg_len = float(sample["avg_line_length"])
        if 35 <= avg_len <= 90:
            base_score += 1.0
        elif 25 <= avg_len < 35 or 90 < avg_len <= 120:
            base_score += 0.8
        elif 20 <= avg_len < 25 or 120 < avg_len <= 150:
            base_score += 0.5
        else:
            base_score += 0.2
        factors += 1

    # File size (accommodate larger modern files)
    if "size" in sample and sample["size"] is not None:
        size = int(sample["size"])
        if 200 <= size <= 8000:
            base_score += 1.0
        elif 100 <= size < 200 or 8000 < size <= 25000:
            base_score += 0.8
        elif 50 <= size < 100 or 25000 < size <= 50000:
            base_score += 0.5
        else:
            base_score += 0.2
        factors += 1

    # License scoring
    if "licenses" in sample and sample["licenses"]:
        licenses = (
            sample["licenses"]
            if isinstance(sample["licenses"], list)
            else [sample["licenses"]]
        )
        has_good_license = any(
            lic in ZENGLOW_QUALITY_THRESHOLDS["preferred_licenses"]
            for lic in licenses
            if lic
        )
        if has_good_license:
            base_score += 1.0
        else:
            base_score += 0.6
        factors += 1

    # Tech stack relevance bonus
    if "content" in sample and sample["content"]:
        content = str(sample["content"]).lower()
        keywords = lang_config.get("keywords", [])
        keyword_matches = sum(1 for keyword in keywords if keyword in content)
        if keyword_matches > 0:
            relevance_bonus = min(0.3, keyword_matches * 0.1)  # Max 30% bonus
            base_score += relevance_bonus * factors  # Apply to all factors

    # Repository name relevance
    if "repository_name" in sample and sample["repository_name"]:
        repo_name = str(sample["repository_name"]).lower()
        keywords = lang_config.get("keywords", [])
        if any(keyword in repo_name for keyword in keywords):
            base_score += 0.2 * factors  # 20% bonus for relevant repositories

    final_score = (base_score / factors if factors > 0 else 0.5) + quality_boost
    return min(1.0, final_score)  # Cap at 1.0


def filter_zenglow_relevant_samples(
    dataset, language: str, min_quality_score: float = 0.5
) -> tuple:
    """
    Filter dataset for ZenGlow tech stack relevance and quality
    """
    if len(dataset) == 0:
        return dataset, {"total": 0, "filtered": 0, "quality_stats": {}}

    original_count = len(dataset)
    indices_to_keep = []
    quality_scores = []
    relevance_scores = []

    lang_config = ZENGLOW_TECH_STACK.get(language, {})
    keywords = lang_config.get("keywords", [])
    file_patterns = lang_config.get("file_patterns", [])

    for i in range(len(dataset)):
        sample = dataset[i]

        # Calculate quality score
        quality_score = calculate_zenglow_quality_score(sample, language)

        if quality_score >= min_quality_score:
            # Calculate relevance score
            relevance_score = 0.0

            # Check content relevance
            if "content" in sample and sample["content"]:
                content = str(sample["content"]).lower()
                keyword_matches = sum(1 for keyword in keywords if keyword in content)
                relevance_score += keyword_matches * 0.2

            # Check file path relevance
            if "path" in sample and sample["path"]:
                path = str(sample["path"]).lower()
                pattern_matches = sum(
                    1 for pattern in file_patterns if pattern.lower() in path
                )
                relevance_score += pattern_matches * 0.3

            # Check repository relevance
            if "repository_name" in sample and sample["repository_name"]:
                repo_name = str(sample["repository_name"]).lower()
                if any(keyword in repo_name for keyword in keywords):
                    relevance_score += 0.5

            indices_to_keep.append(i)
            quality_scores.append(quality_score)
            relevance_scores.append(relevance_score)

    # Sort by combined score (quality + relevance)
    if indices_to_keep:
        combined_scores = [
            (q + r, idx)
            for q, r, idx in zip(quality_scores, relevance_scores, indices_to_keep)
        ]
        combined_scores.sort(reverse=True)

        # Take top samples, maintaining order
        indices_to_keep = [idx for _, idx in combined_scores]
        quality_scores = [
            quality_scores[indices_to_keep.index(idx)] for _, idx in combined_scores
        ]
        relevance_scores = [
            relevance_scores[indices_to_keep.index(idx)] for _, idx in combined_scores
        ]

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
            "mean_quality": statistics.mean(quality_scores) if quality_scores else 0,
            "mean_relevance": (
                statistics.mean(relevance_scores) if relevance_scores else 0
            ),
            "min_quality": min(quality_scores) if quality_scores else 0,
            "max_quality": max(quality_scores) if quality_scores else 0,
        },
    }

    return filtered_dataset, stats


def process_zenglow_language(
    language: str,
    max_samples: int = 1000,
    min_quality_score: float = 0.5,
    output_dir: Optional[str] = None,
) -> bool:
    """
    Process a language specifically for ZenGlow tech stack needs
    """
    if language not in ZENGLOW_TECH_STACK:
        print(f"⚠️  Language {language} not in ZenGlow tech stack")
        return False

    if output_dir is None:
        output_dir = OUTPUT_BASE_DIR

    lang_config = ZENGLOW_TECH_STACK[language]

    try:
        print(f"🔄 Loading {language} dataset for ZenGlow tech stack...")
        print(
            f"🎯 Priority: {lang_config['priority']} | Weight modifier: {lang_config['weight_modifier']}"
        )

        # Load dataset
        dataset = load_dataset(
            "bigcode/the-stack-smol", data_dir=f"data/{language}", split="train"
        )
        print(f"✅ Dataset {language} loaded: {len(dataset)} samples")

        # Apply ZenGlow-specific filtering
        print(f"🔍 Applying ZenGlow tech stack filtering...")
        print(f"🔍 Target keywords: {', '.join(lang_config['keywords'][:5])}...")

        dataset, filter_stats = filter_zenglow_relevant_samples(
            dataset, language, min_quality_score
        )

        print(f"📊 ZenGlow filtering results:")
        print(f"   Original: {filter_stats['total']} samples")
        print(
            f"   Filtered: {filter_stats['filtered']} samples ({filter_stats['filter_ratio']:.1%} retained)"
        )
        print(f"   Avg quality: {filter_stats['quality_stats']['mean_quality']:.2f}")
        print(
            f"   Avg relevance: {filter_stats['quality_stats']['mean_relevance']:.2f}"
        )

        # Limit to max_samples if specified
        if len(dataset) > max_samples:
            print(f"📊 Limiting to top {max_samples} samples...")
            dataset = dataset.select(range(max_samples))

        final_count = len(dataset)
        if final_count == 0:
            print(f"⚠️  No samples passed filtering for {language}")
            return False

        # Save results
        lang_dir = Path(output_dir) / language
        lang_dir.mkdir(parents=True, exist_ok=True)

        output_path = lang_dir / "zenglow_curated.json"
        dataset.to_json(str(output_path))
        print(f"💾 Curated dataset saved: {output_path}")

        # Create ZenGlow-specific sidecar metadata
        create_zenglow_sidecar(
            output_path, language, final_count, filter_stats, lang_config
        )

        return True

    except Exception as e:
        print(f"❌ Error processing {language}: {e}")
        return False


def create_zenglow_sidecar(
    data_path: Path,
    language: str,
    sample_count: int,
    filter_stats: Dict[str, Any],
    lang_config: Dict[str, Any],
) -> None:
    """Create ZenGlow-specific sidecar metadata"""
    sidecar_path = data_path.with_suffix(data_path.suffix + ".meta.json")

    metadata = {
        "author": "ZenGlow Tech Stack Curator",
        "status": "curated",
        "version": "1.0",
        "priority": lang_config["priority"],
        "tags": [
            "programming",
            f"lang-{language}",
            "zenglow-tech-stack",
            "curated",
            "quality-filtered",
            "relevance-scored",
        ]
        + lang_config["keywords"][:3],  # Add top keywords as tags
        # Data source info
        "data_source": "bigcode/the-stack-smol",
        "language": language,
        "sample_count": sample_count,
        "curation_method": "zenglow_tech_stack_relevance",
        # ZenGlow-specific config
        "weight_modifier": lang_config["weight_modifier"],
        "quality_boost": lang_config.get("quality_boost", 0.0),
        "target_keywords": lang_config["keywords"],
        "file_patterns": lang_config["file_patterns"],
        # Quality metrics
        "filter_stats": filter_stats,
        "avg_quality_score": filter_stats["quality_stats"]["mean_quality"],
        "avg_relevance_score": filter_stats["quality_stats"]["mean_relevance"],
        # ZenGlow integration
        "content_type": "curated_code_repository",
        "processing_notes": f"Curated {sample_count} samples for ZenGlow {language} development",
        "use_cases": [
            "Code examples and patterns",
            "Best practices reference",
            "RAG-based code assistance",
            "Development documentation",
        ],
    }

    with open(sidecar_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"📝 ZenGlow sidecar metadata created: {sidecar_path}")


def main():
    """Process ZenGlow tech stack languages"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Curate the-stack-smol for ZenGlow tech stack"
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        choices=list(ZENGLOW_TECH_STACK.keys()),
        default=list(ZENGLOW_TECH_STACK.keys()),
        help="Languages to process",
    )
    parser.add_argument(
        "--max-samples", type=int, default=1000, help="Maximum samples per language"
    )
    parser.add_argument(
        "--min-quality", type=float, default=0.5, help="Minimum quality score (0.0-1.0)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=OUTPUT_BASE_DIR, help="Output directory"
    )
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Process only critical and high priority languages",
    )

    args = parser.parse_args()

    languages = args.languages
    if args.priority_only:
        languages = [
            lang
            for lang in languages
            if ZENGLOW_TECH_STACK[lang]["priority"] in ["critical", "high"]
        ]

    print(f"🚀 ZenGlow Tech Stack Curation")
    print(f"📊 Processing {len(languages)} languages: {', '.join(languages)}")
    print(f"🎯 Max samples per language: {args.max_samples}")
    print(f"🎯 Min quality score: {args.min_quality}")

    results = {"success": [], "failed": []}

    for i, language in enumerate(languages, 1):
        print(f"\n[{i}/{len(languages)}] Processing {language}...")

        success = process_zenglow_language(
            language=language,
            max_samples=args.max_samples,
            min_quality_score=args.min_quality,
            output_dir=args.output_dir,
        )

        if success:
            results["success"].append(language)
            print(f"✅ {language} completed successfully")
        else:
            results["failed"].append(language)
            print(f"❌ {language} failed")

    # Summary
    print(f"\n📈 ZenGlow Curation Complete!")
    print(f"✅ Successful: {len(results['success'])} languages")
    print(f"❌ Failed: {len(results['failed'])} languages")

    if results["success"]:
        print(f"\n🎯 Next steps:")
        print(f"1. Review curated data in: {args.output_dir}")
        print(f"2. Integrate with ZenGlow pipeline:")
        for lang in results["success"]:
            print(
                f"   python scripts/enhanced_intake_to_redis.py --source {args.output_dir}/{lang}/zenglow_curated.json"
            )


if __name__ == "__main__":
    main()
