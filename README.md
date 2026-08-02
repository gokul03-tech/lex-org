---
license: apache-2.0
---

# Mistral 7B Instruct

AWQ quantized model using https://github.com/casper-hansen/AutoAWQ.

Dependencies:

```
pip install git+https://github.com/huggingface/transformers.git
pip install git+https://github.com/casper-hansen/AutoAWQ.git
```

Example:

```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer, TextStreamer

quant_path = "mistral-7b-instruct-v0.1"

# Load model
model = AutoAWQForCausalLM.from_quantized(quant_path, fuse_layers=True)
tokenizer = AutoTokenizer.from_pretrained(quant_path, trust_remote_code=True)
streamer = TextStreamer(tokenizer, skip_special_tokens=True)

# Convert prompt to tokens
text = "<s>[INST] What is your favourite condiment? [/INST]"
"Well, I'm quite partial to a good squeeze of fresh lemon juice. It adds just the right amount of zesty flavour to whatever I'm cooking up in the kitchen!</s> "
"[INST] Do you have mayonnaise recipes? [/INST]"

tokens = tokenizer(
    text, 
    return_tensors='pt'
).input_ids.cuda()

# Generate output
generation_output = model.generate(
    tokens, 
    streamer=streamer,
    max_new_tokens=512
)
```

### vLLM

Support is added to vLLM:

```
pip install git+https://github.com/mistralai/vllm-release@add-mistral
```

Run using this model:

```python
from vllm import LLM, SamplingParams

prompts = [
    "Hello, my name is",
    "The president of the United States is",
    "The capital of France is",
    "The future of AI is",
]
sampling_params = SamplingParams(temperature=0.8, top_p=0.95)

llm = LLM(model="casperhansen/mistral-7b-instruct-v0.1-awq", quantization="awq", dtype="half")

outputs = llm.generate(prompts, sampling_params)

# Print the outputs.
for output in outputs:
    prompt = output.prompt
    generated_text = output.outputs[0].text
    print(f"Prompt: {prompt!r}, Generated text: {generated_text!r}")

```