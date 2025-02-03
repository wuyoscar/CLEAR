#!/usr/bin/env python3

import argparse
import json
import torch
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported

def main():
    # ---------------------------
    # Parse Command-line Arguments
    # ---------------------------
    parser = argparse.ArgumentParser(description="Fine-tune a Llama-based model with LoRA.")
    parser.add_argument("--hf_token", type=str, default="", help="Hugging Face token (for gated models).")
    parser.add_argument("--model_save_name", type=str, default="llama-3b-instruct",
                        help="Directory or repository name for saving the model.")
    parser.add_argument("--base_model_name", type=str, default="meta-llama/Llama-3.2-3B-Instruct",
                        help="Base model name or path.")
    parser.add_argument("--data_path", type=str, default="io_dataset_instruct.json",
                        help="Path to the JSON file with training data.")
    parser.add_argument("--max_seq_length", type=int, default=1024, help="Max sequence length.")
    parser.add_argument("--dtype", type=str, default=None, 
                        help='Override data type, e.g. "float16". If None, auto-detect is used.')
    parser.add_argument("--load_in_4bit", action="store_true",
                        help="Use 4-bit quantization to reduce memory usage (default False).")
    parser.add_argument("--train_epochs", type=int, default=10, help="Number of training epochs.")
    parser.add_argument("--batch_size", type=int, default=6, help="Per-device train batch size.")
    parser.add_argument("--grad_acc_steps", type=int, default=8, help="Gradient accumulation steps.")
    parser.add_argument("--learning_rate", type=float, default=5e-5, help="Learning rate for fine-tuning.")
    parser.add_argument("--warmup_ratio", type=float, default=0.2, help="Warmup ratio for LR scheduler.")
    parser.add_argument("--no_bf16", action="store_true",
                        help="Disable bf16 if you are on a device that does not support it.")
    parser.add_argument("--save_merged_16bit", action="store_true",
                        help="Whether to merge LoRA into 16-bit and save.")
    parser.add_argument("--push_merged_16bit", action="store_true",
                        help="Whether to merge LoRA into 16-bit and push to HF Hub.")
    args = parser.parse_args()

    # ---------------------------
    # Load Base Model & Tokenizer
    # ---------------------------
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model_name,
        max_seq_length=args.max_seq_length,
        dtype=args.dtype,                 # e.g., "float16" or None for auto
        load_in_4bit=args.load_in_4bit,   # True or False
        token=args.hf_token
    )

    # ---------------------------
    # Wrap Base Model in LoRA
    # ---------------------------
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,   # LoRA rank
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",  # or True/"unsloth"
        random_state=3407,
        use_rslora=False,
        loftq_config=None
    )

    # ---------------------------
    # Load Training Data
    # ---------------------------
    with open(args.data_path, "r") as f:
        data = json.load(f)

    dataset = Dataset.from_list(data)

    # Format data for Alpaca-like prompts
    alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Your response must be a valid JSON object, strictly following the requested format.

### Instruction:
{}

### Input:
{}

### Response (valid JSON only):
{}
"""

    eos_token = tokenizer.eos_token

    def formatting_prompts_func(examples):
        instructions = examples["instruction"]
        inputs       = examples["input"]
        outputs      = examples["output"]
        texts = []
        for instruction, input_text, output in zip(instructions, inputs, outputs):
            text = alpaca_prompt.format(instruction, input_text, output) + eos_token
            texts.append(text)
        return { "text" : texts }

    dataset = dataset.map(
       formatting_prompts_func,
       batched=True,
       remove_columns=dataset.column_names
    )

    # ---------------------------
    # Setup Trainer
    # ---------------------------
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        dataset_num_proc=4,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_acc_steps,
            num_train_epochs=args.train_epochs,
            warmup_ratio=args.warmup_ratio,
            learning_rate=args.learning_rate,
            optim="adamw_8bit",
            weight_decay=0.05,
            lr_scheduler_type="cosine",
            fp16=False,
            bf16=not args.no_bf16 and is_bfloat16_supported(),
            logging_steps=3,
            output_dir=args.model_save_name,
            seed=3407,
            report_to="none"
        )
    )

    # ---------------------------
    # Train
    # ---------------------------
    if not hasattr(trainer, "trained"):
        trainer_stats = trainer.train()
        trainer.trained = True
        print(f"Training complete. Stats: {trainer_stats}")
    else:
        print("Model has already been trained! Skipping to avoid double training.")

    # ---------------------------
    # (Optional) Merge & Save
    # ---------------------------
    if args.save_merged_16bit:
        print("Merging LoRA into 16-bit weights and saving locally...")
        model.save_pretrained_merged(
            args.model_save_name,
            tokenizer,
            save_method="merged_16bit"
        )
        print(f"Model merged + saved to {args.model_save_name} (16-bit).")

    if args.push_merged_16bit:
        print("Merging LoRA into 16-bit weights and pushing to Hugging Face Hub...")
        model.push_to_hub_merged(
            args.model_save_name,
            tokenizer,
            save_method="merged_16bit",
            token=args.hf_token
        )
        print(f"Model merged + pushed to HF Hub repo {args.model_save_name}.")

if __name__ == "__main__":
    main()
