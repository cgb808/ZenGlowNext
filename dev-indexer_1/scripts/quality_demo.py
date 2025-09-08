#!/usr/bin/env python3
"""
Quality Demonstration Script
Shows how quality filtering works with sample data
"""


def demonstrate_quality_scoring():
    """Demonstrate the quality scoring algorithm"""

    # Sample code entries with different quality characteristics
    samples = [
        {
            "name": "High Quality Python",
            "alphanum_fraction": 0.75,
            "avg_line_length": 65,
            "size": 1200,
            "licenses": ["MIT"],
        },
        {
            "name": "Poor Quality (Too Long Lines)",
            "alphanum_fraction": 0.70,
            "avg_line_length": 150,  # Too long
            "size": 800,
            "licenses": ["MIT"],
        },
        {
            "name": "Excellent Rust Code",
            "alphanum_fraction": 0.78,
            "avg_line_length": 55,
            "size": 2500,
            "licenses": ["Apache-2.0"],
        },
        {
            "name": "Low Quality (Mostly Comments)",
            "alphanum_fraction": 0.35,  # Too many comments
            "avg_line_length": 45,
            "size": 600,
            "licenses": ["MIT"],
        },
    ]

    print("🎯 Quality Scoring Demonstration")
    print("=" * 50)

    for sample in samples:
        # Simulate the quality scoring from our script
        score = 0.0
        factors = 0

        # Alphanum scoring
        alphanum = sample["alphanum_fraction"]
        if 0.6 <= alphanum <= 0.8:
            alphanum_score = 1.0
        elif 0.5 <= alphanum < 0.6 or 0.8 < alphanum <= 0.9:
            alphanum_score = 0.7
        elif alphanum >= 0.5:
            alphanum_score = 0.3
        else:
            alphanum_score = 0.0
        score += alphanum_score
        factors += 1

        # Line length scoring
        avg_len = sample["avg_line_length"]
        if 40 <= avg_len <= 80:
            length_score = 1.0
        elif 30 <= avg_len < 40 or 80 < avg_len <= 100:
            length_score = 0.7
        elif 20 <= avg_len < 30 or 100 < avg_len <= 120:
            length_score = 0.4
        else:
            length_score = 0.1
        score += length_score
        factors += 1

        # Size scoring
        size = sample["size"]
        if 500 <= size <= 5000:
            size_score = 1.0
        elif 200 <= size < 500 or 5000 < size <= 15000:
            size_score = 0.7
        elif 100 <= size < 200 or 15000 < size <= 30000:
            size_score = 0.4
        else:
            size_score = 0.1
        score += size_score
        factors += 1

        # License scoring
        good_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause"]
        if any(lic in good_licenses for lic in sample["licenses"]):
            license_score = 1.0
        else:
            license_score = 0.5
        score += license_score
        factors += 1

        final_score = score / factors

        print(f"\n📄 {sample['name']}")
        print(f"   Alphanum fraction: {alphanum:.2f} → {alphanum_score:.1f}/1.0")
        print(f"   Avg line length: {avg_len:3d} → {length_score:.1f}/1.0")
        print(f"   File size: {size:4d} bytes → {size_score:.1f}/1.0")
        print(f"   License: {sample['licenses'][0]} → {license_score:.1f}/1.0")
        print(f"   🎯 Final Score: {final_score:.2f}/1.0", end="")

        if final_score >= 0.8:
            print(" ⭐ EXCELLENT")
        elif final_score >= 0.6:
            print(" ✅ GOOD")
        elif final_score >= 0.4:
            print(" ⚠️  FAIR")
        else:
            print(" ❌ POOR")


if __name__ == "__main__":
    demonstrate_quality_scoring()

    print(f"\n{'=' * 50}")
    print("💡 ZenGlow Benefits:")
    print("• High-quality code gets weight_modifier: 1.2")
    print("• Better retrieval priority in RAG system")
    print("• License-compliant examples only")
    print("• Readable, well-structured code samples")
    print("• Repository provenance for attribution")
