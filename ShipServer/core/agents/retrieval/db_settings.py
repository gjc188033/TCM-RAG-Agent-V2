import os

# PostgreSQL 术语库配置
PG_HOST = "10.28.124.91"
PG_PORT = 5432
PG_DATABASE = "ship_terminology"
PG_USER = "ship_agent"
PG_PASSWORD = "ship_agent"

# Elasticsearch数据库配置
ELASTICSEARCH_URI = "http://10.28.124.91:9200"
ELASTICSEARCH_USER = None
ELASTICSEARCH_PASSWORD = None
ELASTICSEARCH_INDEX = "ship_regulations"

# 构造 bge-m3 模型的路径
BGE_M3_MODEL_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "models", "bge-m3"))
print(f"使用bge-m3模型路径: {BGE_M3_MODEL_PATH}")

# bge-reranker 模型路径
BGE_RERANKER_MODEL_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "models", "bge-reranker"))
print(f"使用bge-reranker模型路径: {BGE_RERANKER_MODEL_PATH}")

# SPLADE模型路径（保留，可用于对比实验）
SPLADE_MODEL_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "models", "splade-v3"))
print(f"使用SPLADE模型路径: {SPLADE_MODEL_PATH}")

# 向量维度配置
DENSE_VECTOR_DIMENSION = 1024   # bge-m3模型的向量维度
SPARSE_VECTOR_DIMENSION = 30522  # SPLADE模型的向量维度