#!/usr/bin/env python3
"""
Specialized Model Router
Routes queries to the appropriate specialized Phi-3 model based on content analysis
"""

from datetime import datetime
import os
from typing import Any, Dict

import httpx


class SpecializedModelRouter:
    """Routes queries to appropriate specialized models"""

    def __init__(self, ollama_url: str | None = None):
        # Prefer env var if not provided, default to common local port 11434
        self.ollama_url: str = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")

        # Model specializations
        self.SPECIALIZED_MODELS: Dict[str, Dict[str, Any]] = {
            "mathematics": {
                "model": "phi3:mini",
                "keywords": [
                    "math",
                    "mathematics",
                    "calculate",
                    "solve",
                    "equation",
                    "number",
                    "add",
                    "subtract",
                    "multiply",
                    "divide",
                    "fraction",
                    "decimal",
                    "algebra",
                    "geometry",
                    "trigonometry",
                    "calculus",
                    "statistics",
                    "problem",
                    "word problem",
                    "percentage",
                    "ratio",
                    "proportion",
                ],
                "training_log": "models/ollama_mathematics_phi3/calculative_training_log_20250829_075730.json",
                "description": "Specialized for mathematical reasoning and problem-solving",
            },
            "english": {
                "model": "phi3:mini",
                "keywords": [
                    "english",
                    "writing",
                    "grammar",
                    "literature",
                    "reading",
                    "comprehension",
                    "essay",
                    "paragraph",
                    "sentence",
                    "vocabulary",
                    "spelling",
                    "poetry",
                    "story",
                    "narrative",
                    "analysis",
                    "interpretation",
                    "language",
                    "text",
                    "author",
                    "character",
                    "theme",
                    "plot",
                    "setting",
                    "dialogue",
                ],
                "training_log": "models/ollama_english_phi3/calculative_training_log_20250829_075921.json",
                "description": "Specialized for English language and literature",
            },
            "general": {
                "model": "phi3:mini",
                "keywords": [],
                "training_log": None,
                "description": "General-purpose model for non-specialized queries",
            },
        }

    def analyze_query_subject(self, query: str) -> str:
        """Analyze query to determine the best specialized model"""
        query_lower = query.lower()

        # Score each specialization
        scores: Dict[str, int] = {}
        for subject, config in self.SPECIALIZED_MODELS.items():
            if subject == "general":
                continue

            score = 0
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    score += 1

            scores[subject] = score

        # Find the highest scoring specialization
        if not scores or max(scores.values()) == 0:
            return "general"

        best_subject = max(scores, key=lambda k: scores[k])
        confidence = scores[best_subject] / max(1, len(query_lower.split())) * 100

        print(f"🎯 Query analysis: '{query[:80]}...'")
        print(f"   Subject: {best_subject} (confidence: {confidence:.1f}%)")
        print(f"   Keywords found: {scores[best_subject]}")

        return best_subject

    def format_specialized_prompt(self, query: str, subject: str) -> str:
        """Format query with subject-specific context"""
        if subject == "mathematics":
            return (
                "[LEARNING_CONTEXT] Mathematics "
                "[LEARNING_OBJECTIVE] Understand and solve mathematical concepts clearly. "
                f"[TASK] {query}"
            )
        elif subject == "english":
            return (
                "[LEARNING_CONTEXT] English Language Arts "
                "[LEARNING_OBJECTIVE] Provide clear analysis and explanation of English concepts. "
                f"[TASK] {query}"
            )
        else:
            return query

    def query_model(self, prompt: str, model_name: str = "phi3:mini") -> str:
        """Send query to specified Ollama model"""
        try:
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "top_p": 0.9},
            }

            response = httpx.post(f"{self.ollama_url}/api/generate", json=payload, timeout=60.0)

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No response received")
            else:
                return f"Error: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Exception during model query: {e}"

    def route_and_respond(self, query: str) -> Dict[str, Any]:
        """Main routing function - analyzes query and returns specialized response"""
        print("🚀 SPECIALIZED MODEL ROUTER")
        print("=" * 50)

        # Analyze query to determine specialization
        subject = self.analyze_query_subject(query)
        model_config = self.SPECIALIZED_MODELS[subject]

        print(f"📚 Using {subject} specialization")
        print(f"   Model: {model_config['model']}")
        print(f"   Description: {model_config['description']}")

        # Format prompt with specialization context
        specialized_prompt = self.format_specialized_prompt(query, subject)

        # Query the model
        print("🤖 Querying model...")
        response = self.query_model(specialized_prompt, model_config["model"])

        # Package the result
        result = {
            "original_query": query,
            "detected_subject": subject,
            "model_used": model_config["model"],
            "specialized_prompt": specialized_prompt,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "router_version": "v1.0",
        }

        return result

    def interactive_mode(self) -> None:
        """Interactive mode for testing the router"""
        print("🎯 INTERACTIVE SPECIALIZED MODEL ROUTER")
        print("=" * 50)
        print("Enter queries to test specialized routing (type 'quit' to exit)")
        print("Examples:")
        print("  - 'What is 25% of 400?'")
        print("  - 'Analyze the theme in Romeo and Juliet'")
        print("  - 'How do you solve quadratic equations?'")
        print()

        while True:
            query = input("📝 Enter your query: ").strip()

            if query.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break

            if not query:
                continue

            print()
            result = self.route_and_respond(query)

            print(f"\n💬 Response from {result['detected_subject']} specialist:")
            print(f"   {result['response'][:300]}...")
            print()
            print("-" * 50)
            print()


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="Specialized Model Router")
    parser.add_argument("--query", help="Single query to route")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument("--test", action="store_true", help="Run test queries")

    args = parser.parse_args()

    router = SpecializedModelRouter()

    if args.query:
        result = router.route_and_respond(args.query)
        print(f"\nResponse: {result['response']}")

    elif args.test:
        test_queries = [
            "What is the area of a circle with radius 5?",
            "Explain the symbolism in The Great Gatsby",
            "How do you solve 2x + 5 = 15?",
            "What are the themes in Hamlet?",
            "Calculate the compound interest on $1000 at 5% for 3 years",
        ]

        for query in test_queries:
            print(f"\n🧪 Test Query: {query}")
            result = router.route_and_respond(query)
            print(f"Response: {result['response'][:200]}...")
            print()

    elif args.interactive:
        router.interactive_mode()

    else:
        print("Please specify --query, --interactive, or --test")


if __name__ == "__main__":
    main()
