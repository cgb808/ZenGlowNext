#!/usr/bin/env python3
"""
GGUF Model Quantization Script for Codespace
Supports GGUF format quantization using llama.cpp integration
"""

import os
import sys
import time
import json
import subprocess
import argparse
from typing import Dict, Any, Optional
import psutil

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("⚠️  llama-cpp-python not available. GGUF functionality limited.")

try:
    from ctransformers import AutoModelForCausalLM, AutoTokenizer
    CTRANSFORMERS_AVAILABLE = True
except ImportError:
    CTRANSFORMERS_AVAILABLE = False


class GGUFQuantizer:
    """GGUF model quantization and validation"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.temp_dir = "/tmp/gguf_models"
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available"""
        deps = {
            "llama_cpp": LLAMA_CPP_AVAILABLE,
            "ctransformers": CTRANSFORMERS_AVAILABLE,
            "llama_cpp_binary": self._check_llama_cpp_binary()
        }
        return deps
    
    def _check_llama_cpp_binary(self) -> bool:
        """Check if llama.cpp binary tools are available"""
        try:
            result = subprocess.run(
                ["python", "-c", "import llama_cpp; print('OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def download_sample_model(self) -> str:
        """Download a small GGUF model for testing"""
        # Use a small quantized model for testing
        model_url = "https://huggingface.co/microsoft/DialoGPT-small-gguf/resolve/main/DialoGPT-small-q4_0.gguf"
        model_filename = "DialoGPT-small-q4_0.gguf"
        model_path = os.path.join(self.temp_dir, model_filename)
        
        if os.path.exists(model_path):
            print(f"✅ Model already exists: {model_path}")
            return model_path
        
        print(f"📥 Downloading sample GGUF model...")
        try:
            import urllib.request
            urllib.request.urlretrieve(model_url, model_path)
            print(f"✅ Downloaded: {model_path}")
            return model_path
        except Exception as e:
            print(f"❌ Failed to download model: {e}")
            # Create a mock model file for testing the pipeline
            mock_path = os.path.join(self.temp_dir, "mock_model.gguf")
            with open(mock_path, 'w') as f:
                f.write("# Mock GGUF model for testing\n")
            print(f"📝 Created mock model for testing: {mock_path}")
            return mock_path
    
    def validate_gguf_loading(self, model_path: str) -> Dict[str, Any]:
        """Validate GGUF model loading and inference"""
        print(f"\n🔄 Testing GGUF model loading: {os.path.basename(model_path)}")
        
        results = {
            "model_path": model_path,
            "file_size_mb": os.path.getsize(model_path) / (1024 * 1024) if os.path.exists(model_path) else 0,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Test with llama-cpp-python if available
        if LLAMA_CPP_AVAILABLE and model_path.endswith('.gguf'):
            try:
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024
                start_time = time.time()
                
                # Initialize with conservative settings for Codespace
                llm = Llama(
                    model_path=model_path,
                    n_ctx=512,  # Smaller context for limited memory
                    n_threads=2,  # Conservative thread count
                    verbose=False
                )
                
                loading_time = time.time() - start_time
                memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                
                print(f"✅ Model loaded with llama-cpp in {loading_time:.2f}s")
                
                # Test inference
                test_prompt = "The benefits of AI include"
                inference_start = time.time()
                
                output = llm(
                    test_prompt,
                    max_tokens=30,
                    temperature=0.7,
                    echo=False
                )
                
                inference_time = time.time() - inference_start
                generated_text = output['choices'][0]['text'] if output.get('choices') else ""
                
                print(f"🎯 Inference completed in {inference_time:.2f}s")
                print(f"📝 Generated: {test_prompt}{generated_text}")
                
                results.update({
                    "llama_cpp_test": {
                        "success": True,
                        "loading_time_s": loading_time,
                        "inference_time_s": inference_time,
                        "memory_usage_mb": memory_after - memory_before,
                        "generated_text": test_prompt + generated_text,
                        "tokens_generated": len(generated_text.split())
                    }
                })
                
                # Clean up
                del llm
                
            except Exception as e:
                print(f"❌ llama-cpp test failed: {str(e)}")
                results["llama_cpp_test"] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Test with ctransformers if available
        if CTRANSFORMERS_AVAILABLE and model_path.endswith('.gguf'):
            try:
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024
                start_time = time.time()
                
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    model_type='gpt2',  # Fallback model type
                    local_files_only=True
                )
                
                loading_time = time.time() - start_time
                memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                
                print(f"✅ Model loaded with ctransformers in {loading_time:.2f}s")
                
                # Test inference
                test_prompt = "AI technology will"
                inference_start = time.time()
                
                output = model(test_prompt, max_new_tokens=20)
                inference_time = time.time() - inference_start
                
                print(f"🎯 ctransformers inference completed in {inference_time:.2f}s")
                print(f"📝 Generated: {output}")
                
                results.update({
                    "ctransformers_test": {
                        "success": True,
                        "loading_time_s": loading_time,
                        "inference_time_s": inference_time,
                        "memory_usage_mb": memory_after - memory_before,
                        "generated_text": output,
                    }
                })
                
            except Exception as e:
                print(f"❌ ctransformers test failed: {str(e)}")
                results["ctransformers_test"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def benchmark_quantization_formats(self) -> Dict[str, Any]:
        """Benchmark different GGUF quantization formats"""
        print("\n🚀 GGUF Quantization Validation for Codespace")
        print("=" * 50)
        
        # Check dependencies
        deps = self.check_dependencies()
        print(f"📋 Dependencies Check:")
        for dep, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {dep}: {available}")
        
        if not any(deps.values()):
            return {
                "error": "No GGUF libraries available",
                "dependencies": deps,
                "recommendations": [
                    "Install llama-cpp-python: pip install llama-cpp-python",
                    "Or install ctransformers: pip install ctransformers"
                ]
            }
        
        # Environment info
        env_info = {
            "total_memory_gb": psutil.virtual_memory().total / (1024**3),
            "available_memory_gb": psutil.virtual_memory().available / (1024**3),
            "cpu_count": psutil.cpu_count(),
            "dependencies": deps
        }
        
        results = {
            "environment": env_info,
            "quantization_tests": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # If a model path is provided, test it
        if self.model_path and os.path.exists(self.model_path):
            test_result = self.validate_gguf_loading(self.model_path)
            results["quantization_tests"].append(test_result)
        else:
            # Download and test a sample model
            try:
                sample_model_path = self.download_sample_model()
                test_result = self.validate_gguf_loading(sample_model_path)
                results["quantization_tests"].append(test_result)
            except Exception as e:
                results["quantization_tests"].append({
                    "error": f"Failed to test sample model: {str(e)}",
                    "success": False
                })
        
        # Generate summary
        successful_tests = [t for t in results["quantization_tests"] 
                          if t.get("llama_cpp_test", {}).get("success") or 
                             t.get("ctransformers_test", {}).get("success")]
        
        results["summary"] = {
            "total_tests": len(results["quantization_tests"]),
            "successful_tests": len(successful_tests),
            "status": "success" if successful_tests else "failed",
            "recommendations": self._generate_recommendations(results)
        }
        
        return results
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> list:
        """Generate recommendations based on test results"""
        recommendations = []
        
        deps = results["environment"]["dependencies"]
        
        if not deps["llama_cpp"] and not deps["ctransformers"]:
            recommendations.append("Install GGUF support: pip install llama-cpp-python")
        
        if results["environment"]["available_memory_gb"] < 2:
            recommendations.append("Consider using smaller models or increasing memory allocation")
        
        successful_tests = len([t for t in results["quantization_tests"] 
                              if t.get("llama_cpp_test", {}).get("success") or 
                                 t.get("ctransformers_test", {}).get("success")])
        
        if successful_tests == 0:
            recommendations.append("Check model format compatibility and file paths")
        elif successful_tests > 0:
            recommendations.append("GGUF quantization is working! Consider using for production")
        
        return recommendations


def main():
    parser = argparse.ArgumentParser(description="GGUF Model Quantization Validation")
    parser.add_argument("--model", help="Path to GGUF model file")
    parser.add_argument("--output", default="gguf_results.json", 
                       help="Output file for results")
    
    args = parser.parse_args()
    
    quantizer = GGUFQuantizer(args.model)
    results = quantizer.benchmark_quantization_formats()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to {args.output}")
    
    # Print summary
    summary = results.get("summary", {})
    print(f"\n📈 GGUF Validation Summary:")
    print(f"Status: {summary.get('status', 'unknown')}")
    print(f"Successful tests: {summary.get('successful_tests', 0)}/{summary.get('total_tests', 0)}")
    
    if summary.get("recommendations"):
        print("\n💡 Recommendations:")
        for rec in summary["recommendations"]:
            print(f"  • {rec}")
    
    if summary.get("status") == "success":
        print("\n🎉 GGUF quantization validation completed successfully!")
    else:
        print("\n⚠️  Some issues detected. Check the detailed results.")


if __name__ == "__main__":
    main()