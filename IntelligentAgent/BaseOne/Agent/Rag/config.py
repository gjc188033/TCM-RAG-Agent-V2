import os

# Milvus数据库配置
MILVUS_URI = "http://10.28.124.91:19530"
MILVUS_USER = "zhineng2021"
MILVUS_PASSWORD = "zhineng2021"
MILVUS_COLLECTION = "ms"

# Elasticsearch数据库配置
ELASTICSEARCH_URI = "http://10.28.124.91:9200"
ELASTICSEARCH_USER = None
ELASTICSEARCH_PASSWORD = None
ELASTICSEARCH_INDEX = "es3"

# 构造 Qwen 模型的路径，指向 Rag/models/Qwen 目录
QWEN_MODEL_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "models", "Qwen"))
print(f"使用模型路径: {QWEN_MODEL_PATH}")

# SPLADE模型路径
SPLADE_MODEL_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "models", "splade-v3"))
print(f"使用SPLADE模型路径: {SPLADE_MODEL_PATH}")

# 向量维度配置
DENSE_VECTOR_DIMENSION = 3584  # Qwen模型的向量维度
SPARSE_VECTOR_DIMENSION = 30522  # SPLADE模型的向量维度