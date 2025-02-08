import openai


def test_openai(base_url, api_key, model):
    """
    这是一个测试OpenAI API的函数。
    它使用指定的API设置与OpenAI的GPT模型进行对话。

    参数:
    user_message (str): 用户输入的消息

    返回:
    bool: 是否成功
    str: 错误信息或者AI助手的回复
    """
    try:
        # 创建OpenAI客户端并发送请求到OpenAI API
        
        openai.api_key = api_key
        openai.api_base = base_url
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
            max_tokens=100,
            timeout=10,
        )
        # 返回AI的回复
        return True, str(response.choices[0].message.content)
    except Exception as e:
        return False, str(e)


def get_openai_models(api_key, base_url=None):
    """
    获取并排序OpenAI模型列表。

    Args:
        api_key (str): OpenAI API密钥。
        base_url (str, optional): OpenAI API基础URL。默认为None，使用openai库的默认设置。

    Returns:
        list: 排序后的模型ID列表。如果发生异常，返回一个空列表。
    """
    try:
        openai.api_key = api_key
        if base_url:
            openai.api_base = base_url

        models = openai.Model.list()

        # 从配置文件或者字典中加载模型权重
        model_weights = {
            "gpt-4o": 10,
            "claude-3-5": 10,
            "gpt-4": 5,
            "claude-3": 6,
            "deepseek": 3,
            "glm": 3,
        }

        def get_model_weight(model_name):
            model_name = model_name.lower()
            for prefix, weight in model_weights.items():
                if model_name.startswith(prefix):
                    return weight
            return 0

        sorted_models = sorted(
            [model.id for model in models], key=lambda x: (-get_model_weight(x), x)
        )
        return sorted_models
    except Exception as e:
        print(f"Error getting OpenAI models: {e}")  # 打印错误日志
        return []
