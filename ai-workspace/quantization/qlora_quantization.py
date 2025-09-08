#!/usr/bin/env python3
"""
Enhanced QLoRA Quantization Script for Codespace
Supports int4/int8 quantization with validation and performance monitoring
"""

import os
import sys
import time
import psutil
import torch
from typing import Dict, Any, Optional, Tuple
import argparse
import json

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
except ImportError as e:
    print(f"❌ Missing required dependencies: {e}")
    print("💡 Install with: pip install -r requirements-quantization.txt")
    sys.exit(1)


class QuantizationValidator:
    """Validates quantized models and measures performance"""
    
    def __init__(self, model_name: str = "HuggingFaceTB/SmolLM2-1.7B-Instruct"):
        self.model_name = model_name
        self.results = {}
        
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage metrics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            "percent": process.memory_percent()
        }
    
    def benchmark_quantization(self, quantization_bits: int = 4) -> Dict[str, Any]:
        """Benchmark model loading and inference with quantization"""
        print(f"\n🔄 Testing {quantization_bits}-bit quantization...")
        
        # Configure quantization
        if quantization_bits == 4:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True
            )
        elif quantization_bits == 8:
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0
            )
        else:
            quantization_config = None
        
        # Measure memory before loading
        memory_before = self.get_memory_usage()
        start_time = time.time()
        
        try:
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Load model with quantization
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16 if quantization_config else "auto"
            )
            
            loading_time = time.time() - start_time
            memory_after_loading = self.get_memory_usage()
            
            print(f"✅ Model loaded in {loading_time:.2f}s")
            
            # Prepare for LoRA if quantized
            if quantization_config:
                model = prepare_model_for_kbit_training(model)
                
                lora_config = LoraConfig(
                    r=16,
                    lora_alpha=32,
                    lora_dropout=0.05,
                    bias="none",
                    task_type="CAUSAL_LM",
                    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
                )
                
                model = get_peft_model(model, lora_config)
                print(f"🔗 LoRA adapters added")
                model.print_trainable_parameters()
            
            # Test inference
            test_prompt = "The future of AI in healthcare is"
            inputs = tokenizer(test_prompt, return_tensors="pt", padding=True)
            
            # Move inputs to same device as model
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            inference_start = time.time()
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=50,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            inference_time = time.time() - inference_start
            memory_after_inference = self.get_memory_usage()
            
            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            print(f"🎯 Inference completed in {inference_time:.2f}s")
            print(f"📝 Generated: {generated_text}")
            
            # Calculate memory usage
            memory_delta_loading = memory_after_loading['rss_mb'] - memory_before['rss_mb']
            memory_delta_inference = memory_after_inference['rss_mb'] - memory_after_loading['rss_mb']
            
            results = {
                "quantization_bits": quantization_bits,
                "model_name": self.model_name,
                "loading_time_s": loading_time,
                "inference_time_s": inference_time,
                "memory_usage": {
                    "before_mb": memory_before['rss_mb'],
                    "after_loading_mb": memory_after_loading['rss_mb'],
                    "after_inference_mb": memory_after_inference['rss_mb'],
                    "delta_loading_mb": memory_delta_loading,
                    "delta_inference_mb": memory_delta_inference
                },
                "generated_text": generated_text,
                "success": True
            }
            
            # Clean up
            del model
            del tokenizer
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            return results
            
        except Exception as e:
            print(f"❌ Error during {quantization_bits}-bit quantization: {str(e)}")
            return {
                "quantization_bits": quantization_bits,
                "error": str(e),
                "success": False
            }
    
    def validate_codespace_environment(self) -> Dict[str, Any]:
        """Validate that the Codespace environment supports quantization"""
        print("\n🔍 Validating Codespace Environment...")
        
        env_info = {
            "python_version": sys.version,
            "torch_version": torch.__version__ if 'torch' in sys.modules else "Not installed",
            "cuda_available": torch.cuda.is_available() if 'torch' in sys.modules else False,
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "total_memory_gb": psutil.virtual_memory().total / (1024**3),
            "available_memory_gb": psutil.virtual_memory().available / (1024**3),
            "cpu_count": psutil.cpu_count(),
        }
        
        if torch.cuda.is_available():
            env_info["gpu_info"] = []
            for i in range(torch.cuda.device_count()):
                gpu_props = torch.cuda.get_device_properties(i)
                env_info["gpu_info"].append({
                    "name": gpu_props.name,
                    "memory_gb": gpu_props.total_memory / (1024**3)
                })
        
        print(f"🐍 Python: {env_info['python_version']}")
        print(f"🔥 PyTorch: {env_info['torch_version']}")
        print(f"🎮 CUDA Available: {env_info['cuda_available']}")
        print(f"💾 Total Memory: {env_info['total_memory_gb']:.1f} GB")
        print(f"💾 Available Memory: {env_info['available_memory_gb']:.1f} GB")
        print(f"⚡ CPU Cores: {env_info['cpu_count']}")
        
        return env_info
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete validation suite"""
        print("🚀 Starting Model Quantization Validation for Codespace")
        print("=" * 60)
        
        # Environment validation
        env_info = self.validate_codespace_environment()
        
        # Test different quantization levels
        quantization_results = []
        
        # Test 4-bit quantization
        result_4bit = self.benchmark_quantization(4)
        quantization_results.append(result_4bit)
        
        # Test 8-bit quantization
        result_8bit = self.benchmark_quantization(8)
        quantization_results.append(result_8bit)
        
        # Test no quantization (baseline)
        print(f"\n🔄 Testing baseline (no quantization)...")
        result_baseline = self.benchmark_quantization(None)
        quantization_results.append(result_baseline)
        
        final_results = {
            "environment": env_info,
            "quantization_results": quantization_results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": self._generate_summary(quantization_results)
        }
        
        return final_results
    
    def _generate_summary(self, results) -> Dict[str, Any]:
        """Generate performance summary"""
        successful_results = [r for r in results if r.get('success', False)]
        
        if not successful_results:
            return {"status": "All tests failed"}
        
        summary = {"status": "success", "performance_comparison": {}}
        
        # Find baseline (no quantization)
        baseline = next((r for r in successful_results if r['quantization_bits'] is None), None)
        
        if baseline:
            summary["performance_comparison"]["baseline"] = {
                "loading_time_s": baseline['loading_time_s'],
                "inference_time_s": baseline['inference_time_s'],
                "memory_usage_mb": baseline['memory_usage']['delta_loading_mb']
            }
        
        # Compare quantized versions
        for result in successful_results:
            if result['quantization_bits'] is not None:
                bits = result['quantization_bits']
                comparison = {
                    "loading_time_s": result['loading_time_s'],
                    "inference_time_s": result['inference_time_s'],
                    "memory_usage_mb": result['memory_usage']['delta_loading_mb']
                }
                
                if baseline:
                    comparison["speedup_loading"] = baseline['loading_time_s'] / result['loading_time_s']
                    comparison["speedup_inference"] = baseline['inference_time_s'] / result['inference_time_s']
                    comparison["memory_reduction"] = (baseline['memory_usage']['delta_loading_mb'] - 
                                                    result['memory_usage']['delta_loading_mb']) / baseline['memory_usage']['delta_loading_mb']
                
                summary["performance_comparison"][f"{bits}bit"] = comparison
        
        return summary


def main():
    parser = argparse.ArgumentParser(description="Model Quantization Validation for Codespace")
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-1.7B-Instruct", 
                       help="Model to test (default: SmolLM2-1.7B)")
    parser.add_argument("--output", default="quantization_results.json",
                       help="Output file for results")
    parser.add_argument("--bits", choices=[4, 8], type=int, 
                       help="Test specific quantization level only")
    
    args = parser.parse_args()
    
    validator = QuantizationValidator(args.model)
    
    if args.bits:
        # Test specific quantization level
        result = validator.benchmark_quantization(args.bits)
        results = {
            "environment": validator.validate_codespace_environment(),
            "quantization_results": [result],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        # Run full validation
        results = validator.run_full_validation()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to {args.output}")
    
    # Print summary
    if "summary" in results:
        print("\n📈 Performance Summary:")
        summary = results["summary"]
        if summary.get("status") == "success":
            print("✅ All quantization tests passed!")
            comparison = summary.get("performance_comparison", {})
            
            if "4bit" in comparison and "baseline" in comparison:
                bit4 = comparison["4bit"]
                baseline = comparison["baseline"]
                memory_savings = bit4.get("memory_reduction", 0) * 100
                print(f"💾 4-bit quantization memory savings: {memory_savings:.1f}%")
                
            if "8bit" in comparison and "baseline" in comparison:
                bit8 = comparison["8bit"]
                memory_savings = bit8.get("memory_reduction", 0) * 100
                print(f"💾 8-bit quantization memory savings: {memory_savings:.1f}%")
        else:
            print("❌ Some tests failed. Check the detailed results.")
    
    print("\n🎉 Validation complete!")


if __name__ == "__main__":
    main()