import os
import sys
from typing import List, Dict, Any
from langchain.schema import Document
from pymilvus import MilvusClient, DataType
from .config import MILVUS_URI, MILVUS_USER, MILVUS_PASSWORD, MILVUS_COLLECTION
from .embeddings import QwenEmbedding


class MilvusDB:

    def __init__(self, uri=MILVUS_URI, user=MILVUS_USER, password=MILVUS_PASSWORD,
                 collection=MILVUS_COLLECTION):  # is 初始化
        self.client = MilvusClient(uri=uri, user=user, password=password)
        self.uri = uri
        self.user = user
        self.password = password
        self.collection_name = collection
        self.embed_dense = QwenEmbedding()
        print("✅ Milvus连接成功")
        print(f"🔌 连接到Milvus数据库: {self.uri}")

    from typing import List, Dict, Any

    def Find_Information(self, query: str, top_k: int = 5, book_filter: List[str] = None) -> list[list[dict]]:
        """
        根据用户输入的 query，在 Milvus 向量数据库中检索最相似的文档片段。

        参数:
            query (str): 用户输入的查询语句（自然语言问题）
            top_k (int): 返回相似结果的数量（默认5条）
            book_filter (List[str]): 书籍名称过滤列表，只返回指定书籍中的内容

        返回:
            List[Dict[str, Any]]: 包含多个字段的检索结果列表（如文本、页码、行号、是否为图片描述）
        """

        # 步骤 1：将用户输入的文本 query 转换为稠密向量（embedding）
        query_embedding = self.embed_dense.embed_query(query)

        # 步骤 2：设置检索参数
        # 使用 IP 内积作为度量方式，nprobe 表示每个查询会考虑的倒排桶数量（影响准确率与性能）
        search_params = {
            "metric_type": "IP",  # 设置相似度度量方式为内积(与数据库索引一致)
            "params": {"nprobe": 10}  # nprobe 越大，检索更准但速度更慢（适用于 IVF 索引类型）
        }

        # 设置表达式过滤器，根据书籍名称过滤
        filter_expr = None
        if book_filter and len(book_filter) > 0:
            # 构建书籍名称过滤表达式
            book_conditions = [f'book_name == "{book}"' for book in book_filter]
            filter_expr = " || ".join(book_conditions)
            print(f"应用书籍过滤: {filter_expr}")

        # 步骤 3：在指定的向量集合中执行相似度搜索
        results = self.client.search(
            collection_name=self.collection_name,  # Milvus 集合名称
            data=[query_embedding],  # 输入向量（必须为二维列表）
            anns_field="vector",  # 检索字段名（使用新的向量字段名）
            search_params=search_params,  # 修正：param -> search_params
            limit=top_k,  # 返回最相似的 top_k 个结果
            output_fields=[  # 只包含存在的字段
                "summary", "text", "book_name", "is_image_description"
            ],
             filter=filter_expr  # 添加过滤表达式
        )

        # 步骤 4：返回检索结果（通常是一个 list[Hit]，你后续可以处理成 dict 列表）
        return results




