from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def load_model_and_tokenizer(model_name: str = "oscarwu/Llama-3.2-3B-CLEAR", device: str = None):
    """
    加载指定的模型和分词器。
    
    Args:
        model_name (str): 模型名称，默认为 "oscarwu/Llama-3.2-3B-CLEAR"
        device (str, optional): 使用的设备（例如 "cuda", "mps", "cpu"）。如果为 None，则自动检测可用设备。
        
    Returns:
        tuple: (model, tokenizer, device) 加载好的模型、分词器和实际使用的设备字符串。
    """
    # 如果没有提供 device 参数，则自动判断可用设备
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # 根据设备选择合适的数据类型
    model_dtype = torch.float16 if device == "mps" else torch.float32
    # 加载模型，并将其移动到指定设备上
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map={"": device},
        torch_dtype=model_dtype,
    )
    model.to(device)
    
    return model, tokenizer, device

if __name__ == "__main__":
    # 调用函数加载模型和分词器
    model, tokenizer, device = load_model_and_tokenizer()
    
    # 示例查询
    query = "How is Dubbo, NSW supporting farmers with drought-resistant crops?"
    from clear.generate_prompt import generate_query_prompt
    test_prompt = generate_query_prompt(query)
    
    # 对生成的 prompt 进行编码，准备输入给模型
    inputs = tokenizer(
        test_prompt,
        padding=True,
        truncation=True,
        max_length=1024,
        return_tensors="pt"
    ).to(device)
    
    # 使用模型生成输出（设置最大新生成的 token 数为 128）
    outputs = model.generate(**inputs, max_new_tokens=128, use_cache=True)
    
    # 解码输出 token 为文本
    test_result = tokenizer.batch_decode(outputs)
    print(test_result)
