#!/usr/bin/env python3
"""
ZenGlow Comprehensive Tech Stack Curator
Enhanced version supporting sensor data, mobile APIs, enterprise tools, and modern dev ecosystem

Processes BigCode "the-stack-smol" dataset with advanced filtering for:
- Sensor/IoT technologies (Arduino, ESP32, Bluetooth, etc.)
- Mobile/Wearable platforms (React Native, health sensors, etc.)
- API Gateway/Enterprise tools (Kong, Kong plugins, microservices)
- Modern development ecosystem (GitHub tools, VS Code extensions, MCP)
- Traditional web stack (React, FastAPI, PostgreSQL, etc.)
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import argparse
from datasets import load_dataset
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_zenglow_config(config_path: str = None) -> Dict[str, Any]:
    """Load ZenGlow tech stack configuration from YAML file."""
    if config_path is None:
        # Default path relative to script location
        script_dir = Path(__file__).parent
        config_path = (
            script_dir.parent
            / "data_sources"
            / "professional_reference"
            / "zenglow_tech_config.yaml"
        )

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded ZenGlow configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        logger.info("Using fallback minimal configuration")
        return get_fallback_config()


def get_fallback_config() -> Dict[str, Any]:
    """Fallback configuration if YAML file is not available."""
    return {
        "tech_stack": {
            "typescript": {
                "priority": "critical",
                "weight_modifier": 1.5,
                "max_samples": 2000,
            },
            "javascript": {
                "priority": "critical",
                "weight_modifier": 1.4,
                "max_samples": 2000,
            },
            "python": {
                "priority": "critical",
                "weight_modifier": 1.4,
                "max_samples": 2000,
            },
            "c": {"priority": "high", "weight_modifier": 1.2, "max_samples": 800},
            "c++": {"priority": "high", "weight_modifier": 1.2, "max_samples": 800},
            "lua": {"priority": "medium", "weight_modifier": 1.3, "max_samples": 400},
        },
        "curation_settings": {
            "default_min_quality": 0.5,
            "quality_thresholds": {
                "min_alphanum_fraction": 0.45,
                "max_avg_line_length": 100,
                "max_max_line_length": 400,
                "min_size": 30,
                "max_size": 100000,
            },
        },
    }


def calculate_zenglow_quality_score(
    sample: Dict[str, Any], language: str, config: Dict[str, Any]
) -> float:
    """Enhanced quality scoring for ZenGlow comprehensive tech stack."""
    base_score = sample.get("quality", 0.0)

    # Extract key metrics
    alphanum_fraction = sample.get("alphanum_fraction", 0.0)
    avg_line_length = sample.get("avg_line_length", 0.0)
    max_line_length = sample.get("max_line_length", 0.0)
    size = sample.get("size", 0)
    content = sample.get("content", "").lower()
    path = sample.get("path", "").lower()
    repository_name = sample.get("repository_name", "").lower()

    quality_score = base_score

    # Apply language-specific quality boosts
    tech_config = config.get("tech_stack", {}).get(language, {})
    quality_boost = tech_config.get("quality_boost", 0.0)
    quality_score += quality_boost

    # Content quality scoring
    if alphanum_fraction >= 0.6:
        quality_score += 0.2
    elif alphanum_fraction >= 0.5:
        quality_score += 0.1

    # Line length optimization (avoid too long or too short)
    if 30 <= avg_line_length <= 80:
        quality_score += 0.15
    elif 20 <= avg_line_length <= 100:
        quality_score += 0.1

    if max_line_length <= 200:
        quality_score += 0.1
    elif max_line_length > 500:
        quality_score -= 0.2

    # File size scoring
    if 100 <= size <= 50000:  # Optimal size range
        quality_score += 0.1
    elif size > 100000:  # Too large
        quality_score -= 0.3
    elif size < 50:  # Too small
        quality_score -= 0.2

    # Enhanced ZenGlow tech stack specific bonuses
    tech_keywords = {
        "sensor_iot": {
            "keywords": [
                "sensor",
                "bluetooth",
                "ble",
                "arduino",
                "esp32",
                "raspberry",
                "i2c",
                "spi",
                "uart",
                "gpio",
                "accelerometer",
                "gyroscope",
                "heart-rate",
                "temperature",
                "humidity",
                "pressure",
                "gps",
                "magnetometer",
                "proximity",
                "light",
                "motion",
                "tilt",
                "orientation",
                "compass",
            ],
            "bonus": 0.25,
        },
        "mobile_wearable": {
            "keywords": [
                "wearable",
                "watch",
                "fitness",
                "health",
                "heart",
                "step",
                "activity",
                "workout",
                "apple-watch",
                "wear-os",
                "fitbit",
                "garmin",
                "polar",
                "samsung-health",
                "healthkit",
                "google-fit",
                "core-motion",
                "healthconnect",
                "wellness",
            ],
            "bonus": 0.2,
        },
        "api_gateway": {
            "keywords": [
                "kong",
                "api-gateway",
                "rate-limit",
                "auth",
                "proxy",
                "load-balancer",
                "middleware",
                "nginx",
                "envoy",
                "traefik",
                "istio",
                "service-mesh",
                "ingress",
                "circuit-breaker",
            ],
            "bonus": 0.2,
        },
        "dev_ecosystem": {
            "keywords": [
                "github",
                "vscode",
                "extension",
                "copilot",
                "mcp",
                "protocol",
                "ai-assistant",
                "automation",
                "workflow",
                "actions",
                "plugin",
                "marketplace",
                "language-server",
            ],
            "bonus": 0.15,
        },
        "connectivity": {
            "keywords": [
                "websocket",
                "mqtt",
                "http",
                "https",
                "ssl",
                "tls",
                "oauth",
                "jwt",
                "api-key",
                "real-time",
                "streaming",
                "pubsub",
                "event-driven",
                "grpc",
                "protobuf",
            ],
            "bonus": 0.15,
        },
        "enterprise": {
            "keywords": [
                "microservice",
                "kubernetes",
                "helm",
                "terraform",
                "ansible",
                "jenkins",
                "monitoring",
                "prometheus",
                "grafana",
                "elk",
                "logging",
                "metrics",
                "tracing",
                "observability",
            ],
            "bonus": 0.1,
        },
        "embedded_firmware": {
            "keywords": [
                "firmware",
                "embedded",
                "driver",
                "kernel",
                "rtos",
                "freertos",
                "zephyr",
                "mbed",
                "bare-metal",
                "bootloader",
                "flash",
                "eeprom",
                "nvs",
                "interrupt",
            ],
            "bonus": 0.2,
        },
    }

    # Apply tech-specific bonuses
    for category, category_data in tech_keywords.items():
        for keyword in category_data["keywords"]:
            if keyword in content or keyword in path or keyword in repository_name:
                quality_score += category_data["bonus"]
                break  # One bonus per category

    # Repository quality indicators - enhanced for comprehensive stack
    quality_repos = [
        # General tech companies
        "microsoft",
        "google",
        "facebook",
        "apple",
        "amazon",
        "netflix",
        "uber",
        "airbnb",
        # API & Infrastructure
        "kong",
        "nginx",
        "redis",
        "postgres",
        "supabase",
        "vercel",
        "expo",
        # IoT & Embedded
        "arduino",
        "espressif",
        "raspberrypi",
        "adafruit",
        "sparkfun",
        "seeed",
        "nordic",
        "ti",
        "stm",
        "freescale",
        "cypress",
        "infineon",
        # AI & ML
        "tensorflow",
        "pytorch",
        "openai",
        "anthropic",
        "huggingface",
        # Dev tools
        "github",
        "vscode",
        "copilot",
        "jetbrains",
        "atlassian",
    ]

    for repo in quality_repos:
        if repo in repository_name:
            quality_score += 0.2
            break

    # Enhanced sensor/IoT specific repository bonuses
    sensor_repos = [
        "arduino",
        "espressif",
        "raspberrypi",
        "adafruit",
        "sparkfun",
        "seeed",
        "nordic",
        "ti",
        "stm",
        "freescale",
        "cypress",
        "infineon",
        "bosch",
        "sensirion",
        "honeywell",
        "analog",
        "maxim",
        "microchip",
    ]

    for repo in sensor_repos:
        if repo in repository_name:
            quality_score += 0.3  # Extra bonus for sensor-specific repos
            break

    # API gateway specific repository bonuses
    gateway_repos = [
        "kong",
        "nginx",
        "envoyproxy",
        "traefik",
        "istio",
        "linkerd",
        "consul",
    ]

    for repo in gateway_repos:
        if repo in repository_name:
            quality_score += 0.25
            break

    # Mobile/Wearable platform bonuses
    mobile_repos = ["expo", "react-native", "flutter", "ionic", "cordova", "xamarin"]
    wearable_repos = ["apple", "google", "samsung", "fitbit", "garmin", "polar"]

    for repo in mobile_repos + wearable_repos:
        if repo in repository_name:
            quality_score += 0.2
            break

    # License scoring (prefer permissive licenses)
    licenses = sample.get("licenses", [])
    if licenses:
        preferred_licenses = config.get("curation_settings", {}).get(
            "preferred_licenses", []
        )
        for license_name in licenses:
            if license_name in preferred_licenses[:4]:  # Top 4 preferred
                quality_score += 0.15
                break
            elif license_name in preferred_licenses:
                quality_score += 0.1
                break

    # File path indicators
    if any(
        indicator in path
        for indicator in ["example", "demo", "tutorial", "guide", "sample"]
    ):
        quality_score += 0.1

    if any(indicator in path for indicator in ["test", "spec", "__test__"]):
        quality_score += 0.05  # Tests are valuable but lower priority

    # Special bonus for sensor/IoT file patterns
    if any(
        pattern in path
        for pattern in ["sensor", "driver", "firmware", "embedded", "iot", "bluetooth"]
    ):
        quality_score += 0.15

    # Special bonus for API gateway patterns
    if any(
        pattern in path
        for pattern in ["kong", "gateway", "proxy", "middleware", "plugin"]
    ):
        quality_score += 0.15

    # Penalize poor quality indicators
    if any(bad in content for bad in ["todo", "fixme", "hack", "broken"]):
        quality_score -= 0.1

    return max(0.0, min(1.0, quality_score))  # Clamp between 0 and 1


def filter_zenglow_relevant_samples(
    dataset, language: str, config: Dict[str, Any], min_quality_score: float = 0.5
) -> Tuple:
    """Filter dataset for ZenGlow comprehensive tech stack relevance and quality."""
    if len(dataset) == 0:
        return dataset, {"total": 0, "filtered": 0, "quality_stats": {}}

    original_count = len(dataset)
    indices_to_keep = []
    quality_scores = []
    relevance_scores = []

    tech_config = config.get("tech_stack", {}).get(language, {})
    keywords = tech_config.get("keywords", [])
    file_patterns = tech_config.get("file_patterns", [])

    for i in range(len(dataset)):
        sample = dataset[i]

        # Calculate quality score
        quality_score = calculate_zenglow_quality_score(sample, language, config)

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
                    relevance_score += 0.4

            # Combined score (quality * 0.7 + relevance * 0.3)
            combined_score = quality_score * 0.7 + min(relevance_score, 1.0) * 0.3

            indices_to_keep.append(i)
            quality_scores.append(quality_score)
            relevance_scores.append(relevance_score)

    filtered_count = len(indices_to_keep)

    # Create filtered dataset
    filtered_dataset = (
        dataset.select(indices_to_keep) if indices_to_keep else dataset.select([])
    )

    # Calculate statistics
    stats = {
        "total": original_count,
        "filtered": filtered_count,
        "quality_stats": {
            "avg_quality": (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0
            ),
            "avg_relevance": (
                sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            ),
            "min_quality": min(quality_scores) if quality_scores else 0,
            "max_quality": max(quality_scores) if quality_scores else 0,
        },
    }

    return filtered_dataset, stats


def process_zenglow_language(
    language: str,
    config: Dict[str, Any],
    max_samples: Optional[int] = None,
    min_quality: float = 0.5,
    save_samples: bool = True,
) -> Dict[str, Any]:
    """Process a specific language from the BigCode dataset for ZenGlow tech stack."""

    logger.info(f"Processing language: {language}")

    # Get tech stack configuration for this language
    tech_config = config.get("tech_stack", {}).get(language, {})
    if not tech_config:
        logger.warning(f"No configuration found for language: {language}")
        return {"error": f"Language {language} not in ZenGlow tech stack"}

    priority = tech_config.get("priority", "medium")
    weight_modifier = tech_config.get("weight_modifier", 1.0)
    configured_max_samples = tech_config.get("max_samples", 1000)

    # Use provided max_samples or fall back to config
    effective_max_samples = max_samples or configured_max_samples

    try:
        # Load the specific language subset
        logger.info(f"Loading {language} subset from the-stack-smol...")
        dataset = load_dataset(
            "bigcode/the-stack-smol",
            data_dir=f"data/{language}",
            split="train",
            streaming=False,
        )

        logger.info(f"Loaded {len(dataset)} samples for {language}")

        # Filter for ZenGlow relevance and quality
        filtered_dataset, stats = filter_zenglow_relevant_samples(
            dataset, language, config, min_quality
        )

        logger.info(
            f"Filtered to {stats['filtered']} relevant samples "
            f"(quality: {stats['quality_stats']['avg_quality']:.3f}, "
            f"relevance: {stats['quality_stats']['avg_relevance']:.3f})"
        )

        # Limit to max samples if specified
        if effective_max_samples and len(filtered_dataset) > effective_max_samples:
            # Sort by quality score and take top samples
            sample_scores = []
            for i in range(len(filtered_dataset)):
                sample = filtered_dataset[i]
                quality_score = calculate_zenglow_quality_score(
                    sample, language, config
                )
                sample_scores.append((i, quality_score))

            # Sort by quality score (descending) and take top samples
            sample_scores.sort(key=lambda x: x[1], reverse=True)
            top_indices = [idx for idx, _ in sample_scores[:effective_max_samples]]
            filtered_dataset = filtered_dataset.select(top_indices)

            logger.info(f"Limited to top {len(filtered_dataset)} samples by quality")

        # Prepare results
        results = {
            "language": language,
            "priority": priority,
            "weight_modifier": weight_modifier,
            "original_count": stats["total"],
            "filtered_count": stats["filtered"],
            "final_count": len(filtered_dataset),
            "quality_stats": stats["quality_stats"],
            "samples": [],
        }

        # Convert to list and add quality scores
        for i in range(len(filtered_dataset)):
            sample = filtered_dataset[i]
            quality_score = calculate_zenglow_quality_score(sample, language, config)

            sample_data = {
                "content": sample.get("content", ""),
                "path": sample.get("path", ""),
                "repository_name": sample.get("repository_name", ""),
                "licenses": sample.get("licenses", []),
                "size": sample.get("size", 0),
                "quality_score": quality_score,
                "alphanum_fraction": sample.get("alphanum_fraction", 0.0),
                "avg_line_length": sample.get("avg_line_length", 0.0),
                "max_line_length": sample.get("max_line_length", 0.0),
            }
            results["samples"].append(sample_data)

        # Save results if requested
        if save_samples:
            output_dir = Path("data_sources/professional_reference/curated")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"zenglow_{language}_curated.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)

            logger.info(
                f"Saved {len(results['samples'])} curated samples to {output_file}"
            )

        return results

    except Exception as e:
        logger.error(f"Error processing {language}: {e}")
        return {"error": str(e), "language": language}


def curate_priority_languages(
    config: Dict[str, Any],
    priorities: List[str] = None,
    max_samples_per_lang: int = 500,
) -> Dict[str, Any]:
    """Curate samples for priority languages in ZenGlow tech stack."""

    if priorities is None:
        priorities = ["critical", "high"]

    tech_stack = config.get("tech_stack", {})
    priority_languages = []

    for language, lang_config in tech_stack.items():
        if lang_config.get("priority") in priorities:
            priority_languages.append(language)

    logger.info(
        f"Processing {len(priority_languages)} priority languages: {priority_languages}"
    )

    results = {
        "summary": {
            "total_languages": len(priority_languages),
            "priorities": priorities,
            "max_samples_per_language": max_samples_per_lang,
        },
        "languages": {},
    }

    for language in priority_languages:
        try:
            lang_results = process_zenglow_language(
                language,
                config,
                max_samples_per_lang,
                min_quality=0.6,
                save_samples=True,
            )
            results["languages"][language] = lang_results

            if "error" not in lang_results:
                logger.info(
                    f"✓ {language}: {lang_results['final_count']} samples "
                    f"(priority: {lang_results['priority']})"
                )
            else:
                logger.error(f"✗ {language}: {lang_results['error']}")

        except Exception as e:
            logger.error(f"Failed to process {language}: {e}")
            results["languages"][language] = {"error": str(e)}

    return results


def main():
    parser = argparse.ArgumentParser(
        description="ZenGlow Comprehensive Tech Stack Curator"
    )
    parser.add_argument("--language", type=str, help="Specific language to process")
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Process only critical and high priority languages",
    )
    parser.add_argument(
        "--max-samples", type=int, default=500, help="Maximum samples per language"
    )
    parser.add_argument(
        "--min-quality", type=float, default=0.5, help="Minimum quality score threshold"
    )
    parser.add_argument("--config", type=str, help="Path to config YAML file")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data_sources/professional_reference/curated",
        help="Output directory for curated samples",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_zenglow_config(args.config)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.language:
        # Process specific language
        results = process_zenglow_language(
            args.language, config, args.max_samples, args.min_quality
        )

        if "error" not in results:
            print(
                f"\n✓ Successfully curated {results['final_count']} samples for {args.language}"
            )
            print(f"  Priority: {results['priority']}")
            print(f"  Average quality: {results['quality_stats']['avg_quality']:.3f}")
        else:
            print(f"\n✗ Error processing {args.language}: {results['error']}")

    elif args.priority_only:
        # Process priority languages
        results = curate_priority_languages(
            config, max_samples_per_lang=args.max_samples
        )

        # Save summary
        summary_file = output_dir / "zenglow_priority_curation_summary.json"
        with open(summary_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✓ Priority curation complete! Summary saved to {summary_file}")

        # Print summary
        successful = sum(
            1
            for lang_result in results["languages"].values()
            if "error" not in lang_result
        )
        total_samples = sum(
            lang_result.get("final_count", 0)
            for lang_result in results["languages"].values()
            if "error" not in lang_result
        )

        print(f"  Languages processed: {successful}/{len(results['languages'])}")
        print(f"  Total curated samples: {total_samples}")

    else:
        # Show available languages
        tech_stack = config.get("tech_stack", {})
        print("\nAvailable languages in ZenGlow tech stack:")

        for priority in ["critical", "high", "medium"]:
            priority_langs = [
                lang
                for lang, conf in tech_stack.items()
                if conf.get("priority") == priority
            ]
            if priority_langs:
                print(f"\n{priority.upper()} priority:")
                for lang in priority_langs:
                    max_samples = tech_stack[lang].get("max_samples", 1000)
                    print(f"  - {lang} (max: {max_samples} samples)")

        print(f"\nUse --language <name> to process a specific language")
        print(f"Use --priority-only to process critical and high priority languages")


if __name__ == "__main__":
    main()
