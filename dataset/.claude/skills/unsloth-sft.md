# Unsloth Supervised Fine-Tuning

Use this skill when the user wants to train, fine-tune, or work with language models using Unsloth for supervised fine-tuning (SFT). This includes tasks like preparing training data, configuring training parameters, running training jobs, and optimizing model performance.

## Overview

Unsloth is a library that makes fine-tuning large language models 2-5x faster and uses 70% less memory. It's designed to work seamlessly with Hugging Face Transformers and provides optimized implementations for popular model architectures.

**Key Benefits:**
- Faster training with optimized kernels
- Reduced memory usage (can train larger models on smaller GPUs)
- Easy integration with Hugging Face ecosystem
- Support for QLoRA, LoRA, and full fine-tuning
- Works with popular models (Llama, Mistral, Phi, Gemma, Qwen, etc.)

## Installation

```bash
# Install unsloth
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

# Or for CUDA 12.1+
pip install "unsloth[cu121-torch230] @ git+https://github.com/unslothai/unsloth.git"

# Install other required packages
pip install --no-deps trl peft accelerate bitsandbytes
```

## Basic Workflow

### 1. Load Model and Tokenizer

```python
from unsloth import FastLanguageModel
import torch

# Configuration
max_seq_length = 2048  # Supports RoPE scaling internally
dtype = None  # Auto-detect (Float16 for Tesla T4/V100, Bfloat16 for Ampere+)
load_in_4bit = True  # Use 4bit quantization to reduce memory

# Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/mistral-7b-v0.3-bnb-4bit",  # or other supported models
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
    # token="hf_..." # Use if accessing gated models
)

# Popular model options:
# - "unsloth/llama-3-8b-bnb-4bit"
# - "unsloth/mistral-7b-v0.3-bnb-4bit"
# - "unsloth/Phi-3-mini-4k-instruct"
# - "unsloth/gemma-2-9b-bnb-4bit"
# - "unsloth/Qwen2.5-7B-bnb-4bit"
```

### 2. Configure LoRA/QLoRA

```python
model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank (higher = more parameters, better quality, slower)
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=16,  # LoRA scaling factor
    lora_dropout=0,  # Supports any dropout, but 0 is optimized
    bias="none",  # Supports "all", "none"
    use_gradient_checkpointing="unsloth",  # Use Unsloth's checkpointing
    random_state=3407,
    use_rslora=False,  # Rank stabilized LoRA
    loftq_config=None,  # LoftQ configuration
)
```

### 3. Prepare Training Data

Unsloth works with Hugging Face datasets. Format your data according to your task:

**Chat/Instruction Format:**
```python
from datasets import load_dataset

# Load dataset
dataset = load_dataset("json", data_files="train.json", split="train")

# Expected format for chat models:
# [
#   {
#     "conversations": [
#       {"from": "human", "value": "What is 2+2?"},
#       {"from": "gpt", "value": "2+2 equals 4."}
#     ]
#   }
# ]

# Or use standard instruction format:
# [
#   {
#     "instruction": "What is 2+2?",
#     "input": "",
#     "output": "2+2 equals 4."
#   }
# ]

# Format with chat template
def formatting_prompts_func(examples):
    convos = examples["conversations"]
    texts = [
        tokenizer.apply_chat_template(
            convo,
            tokenize=False,
            add_generation_prompt=False
        )
        for convo in convos
    ]
    return {"text": texts}

dataset = dataset.map(formatting_prompts_func, batched=True)
```

**Custom Prompt Template:**
```python
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs = examples["input"]
    outputs = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction, input, output) + tokenizer.eos_token
        texts.append(text)
    return {"text": texts}

dataset = dataset.map(formatting_prompts_func, batched=True)
```

### 4. Configure Training

```python
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    dataset_num_proc=2,
    packing=False,  # Can make training 5x faster for short sequences
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,
        num_train_epochs=1,  # Or use max_steps
        # max_steps=60,
        learning_rate=2e-4,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
        report_to="none",  # Use "wandb" for Weights & Biases logging
    ),
)
```

### 5. Train the Model

```python
# Show memory usage before training
gpu_stats = torch.cuda.get_device_properties(0)
start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
print(f"{start_gpu_memory} GB of memory reserved.")

# Train
trainer_stats = trainer.train()

# Show memory usage after training
used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
used_percentage = round(used_memory / max_memory * 100, 3)
lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
print(f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training.")
print(f"Peak reserved memory = {used_memory} GB.")
print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
print(f"Peak reserved memory % of max memory = {used_percentage} %.")
print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")
```

### 6. Inference

```python
# Enable native 2x faster inference
FastLanguageModel.for_inference(model)

inputs = tokenizer(
    [
        alpaca_prompt.format(
            "Continue the fibonacci sequence.",
            "1, 1, 2, 3, 5, 8",
            "",  # output - leave blank for generation
        )
    ],
    return_tensors="pt"
).to("cuda")

outputs = model.generate(
    **inputs,
    max_new_tokens=64,
    use_cache=True,
    temperature=1.5,
    min_p=0.1
)
decoded = tokenizer.batch_decode(outputs)
print(decoded[0])

# For streaming inference
from transformers import TextStreamer
text_streamer = TextStreamer(tokenizer, skip_prompt=True)
_ = model.generate(**inputs, streamer=text_streamer, max_new_tokens=128)
```

### 7. Save and Export

```python
# Save LoRA adapters
model.save_pretrained("lora_model")
tokenizer.save_pretrained("lora_model")

# Save to 16bit for VLLM or other inference engines
model.save_pretrained_merged("model", tokenizer, save_method="merged_16bit")

# Save to 4bit for later use
model.save_pretrained_merged("model", tokenizer, save_method="merged_4bit")

# Push to Hugging Face Hub
model.push_to_hub_merged("username/model-name", tokenizer, save_method="merged_16bit", token="...")

# Save to GGUF format for llama.cpp
model.save_pretrained_gguf("model", tokenizer, quantization_method="q4_k_m")
model.push_to_hub_gguf("username/model-name", tokenizer, quantization_method="q4_k_m", token="...")
```

## Advanced Configuration

### Memory Optimization

```python
# Enable gradient checkpointing for lower memory
use_gradient_checkpointing="unsloth"

# Use 4-bit quantization
load_in_4bit=True

# Reduce batch size and increase gradient accumulation
per_device_train_batch_size=1
gradient_accumulation_steps=8

# Pack sequences (for datasets with short sequences)
packing=True
```

### Training Optimization

```python
# Use 8-bit optimizers
optim="adamw_8bit"

# Learning rate scheduling
lr_scheduler_type="cosine"  # or "linear", "constant"
warmup_ratio=0.1  # or warmup_steps

# Mixed precision training
fp16=not is_bfloat16_supported()
bf16=is_bfloat16_supported()

# Gradient clipping
max_grad_norm=0.3
```

### LoRA Configuration

```python
# Higher rank for better quality (but slower and more memory)
r=32

# Target all linear layers for maximum adaptation
target_modules=[
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# Use RSLoRA for better stability with high ranks
use_rslora=True  # When r > 16
```

## Common Patterns

### Multi-GPU Training

```python
# Unsloth supports single GPU only for now
# For multi-GPU, use standard Hugging Face Accelerate:
# accelerate launch --multi_gpu train.py
```

### Evaluation During Training

```python
# Add validation dataset
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    args=TrainingArguments(
        # ... other args
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        load_best_model_at_end=True,
    ),
)
```

### Resume Training

```python
# Resume from checkpoint
trainer.train(resume_from_checkpoint="outputs/checkpoint-100")
```

### Custom Loss Functions

```python
# For custom training loops, access the model directly
from torch.nn import CrossEntropyLoss

# Unsloth models are still standard PyTorch models
outputs = model(input_ids=input_ids, labels=labels)
loss = outputs.loss
```

## Troubleshooting

### Out of Memory Errors
1. Reduce `max_seq_length`
2. Reduce `per_device_train_batch_size`
3. Increase `gradient_accumulation_steps`
4. Enable `gradient_checkpointing`
5. Use `load_in_4bit=True`
6. Reduce LoRA rank `r`

### Slow Training
1. Enable `packing=True` for short sequences
2. Increase `per_device_train_batch_size`
3. Use `bf16=True` on Ampere+ GPUs
4. Ensure `use_gradient_checkpointing="unsloth"`

### Quality Issues
1. Increase LoRA rank `r` (try 32, 64)
2. Add more target modules
3. Train for more epochs
4. Adjust learning rate (try 1e-4 to 5e-4)
5. Ensure data quality and format

### NaN Loss
1. Reduce learning rate
2. Enable `max_grad_norm` clipping
3. Check data for issues
4. Use `fp16=False, bf16=True` if available

## Best Practices

1. **Start small**: Test with a small dataset first to verify pipeline
2. **Monitor loss**: Watch for NaN or exploding gradients
3. **Save checkpoints**: Use `save_steps` to avoid losing progress
4. **Validate format**: Ensure data matches expected template format
5. **Test inference**: Verify model generates expected outputs before full training
6. **Use chat templates**: Leverage model's built-in chat template when available
7. **Experiment with LoRA rank**: Start with r=16, increase if needed
8. **Log to W&B**: Use `report_to="wandb"` for better experiment tracking

## Resources

- Unsloth GitHub: https://github.com/unslothai/unsloth
- Unsloth Documentation: https://docs.unsloth.ai
- Example notebooks: https://github.com/unslothai/unsloth/tree/main/notebooks
- Supported models: Check Unsloth model hub on Hugging Face

## Keywords

Use this skill when the user mentions: unsloth, fine-tuning, SFT, supervised fine-tuning, LoRA, QLoRA, train language model, train LLM, model training, adapter training, parameter-efficient fine-tuning, PEFT, llama training, mistral training
