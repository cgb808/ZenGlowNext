import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# --- 1. The Magic: Configure 4-bit Quantization (QLoRA) ---
# This tells the model to load in a super-efficient 4-bit format.
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

# --- 2. Load the Quantized Base Model ---
model_name = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)

# We pass the quantization_config here. This is the key step.
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=quantization_config,
    device_map="auto" # This will automatically use your GPU
)
print("Base model loaded in 4-bit!")

# --- 3. Prepare the model for LoRA ---
# This freezes the original weights and prepares for LoRA adapters.
model = prepare_model_for_kbit_training(model)

# --- 4. Configure LoRA (The "Sticky Notes") ---
# We define how we want our LoRA adapters to behave.
lora_config = LoraConfig(
    r=16, # The rank of the update matrices. Higher rank means more parameters to train. 16 is a good starting point.
    lora_alpha=32, # A scaling factor.
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# --- 5. Combine the Model with LoRA ---
# This applies the LoRA adapters to your quantized model.
model = get_peft_model(model, lora_config)
print("LoRA adapters added to the model.")
model.print_trainable_parameters() # This will show you how few parameters you are actually training!

# From here, you would set up your dataset and use the Hugging Face Trainer
# to run the fine-tuning process. The VRAM usage will be dramatically lower
# than with standard fine-tuning.

# Example of how you would proceed with the Trainer (requires a dataset)
#
# from transformers import TrainingArguments, Trainer
#
# trainer = Trainer(
#     model=model,
#     train_dataset=your_dataset, # You would need to provide a dataset here
#     args=TrainingArguments(
#         per_device_train_batch_size=1,
#         gradient_accumulation_steps=4,
#         max_steps=100, # A short example run
#         learning_rate=2e-4,
#         output_dir="./qlora-results",
#         logging_steps=10,
#     ),
#     data_collator=... # You'd need a data collator here
# )
#
# print("Starting QLoRA fine-tuning...")
# trainer.train()