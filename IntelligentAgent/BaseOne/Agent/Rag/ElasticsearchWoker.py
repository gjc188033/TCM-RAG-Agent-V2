import os
import sys
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from .config import (
    ELASTICSEARCH_URI,
    ELASTICSEARCH_USER,
    ELASTICSEARCH_PASSWORD,
    ELASTICSEARCH_INDEX,
    QWEN_MODEL_PATH,
    DENSE_VECTOR_DIMENSION,
    SPLADE_MODEL_PATH,
    SPARSE_VECTOR_DIMENSION
)
from .embeddings import QwenEmbedding, SpladeEmbedding
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用Elasticsearch和HTTP相关库的日志
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logging.getLogger('elastic_transport').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)


class ElasticsearchDB:
    """
    Elasticsearch数据库客户端
    处理ES连接、索引管理和数据操作
    专为SPLADE稀疏向量优化
    """

    def __init__(self, uri=ELASTICSEARCH_URI, user=ELASTICSEARCH_USER, password=ELASTICSEARCH_PASSWORD,
                 index_name=ELASTICSEARCH_INDEX):
        """
        初始化Elasticsearch客户端
        
        参数:
            uri: Elasticsearch服务器地址
            user: 用户名
            password: 密码
            index_name: 索引名称
        """
        # 构建连接配置
        self.uri = uri
        self.user = user
        self.password = password
        self.index_name = index_name

        print(f"🔌 连接到Elasticsearch: {self.uri}")
        try:
            # 根据是否提供认证信息决定连接方式
            if self.user and self.password:
                self.client = Elasticsearch(
                    [self.uri],
                    basic_auth=(self.user, self.password),
                    verify_certs=False
                )
            else:
                # 无认证模式
                self.client = Elasticsearch([self.uri], verify_certs=False)

            if not self.client.ping():
                raise ConnectionError("无法连接到Elasticsearch")

            print("✅ Elasticsearch连接成功")
            print(f"📚 使用索引: {self.index_name}")

            # 初始化嵌入模型
            self.sparse_embed_model = SpladeEmbedding()

        except Exception as e:
            print(f"❌ Elasticsearch连接失败: {str(e)}")
            raise

    def get_all_book_names(self) -> List[str]:
        """
        获取索引中所有唯一的书名（直接使用 book_name 字段）

        返回:
            List[str]: 所有唯一的书籍名称列表
        """
        try:
            # 构造聚合查询 - 直接使用 book_name.keyword
            query_body = {
                "size": 0,  # 不需要返回文档，只需要聚合结果
                "aggs": {
                    "unique_books": {
                        "terms": {
                            "field": "book_name",  # 明确指定字段名
                            "size": 10000  # 可根据实际数据量调整（避免遗漏）
                        }
                    }
                }
            }

            # 执行查询
            response = self.client.search(
                index=self.index_name,
                body=query_body
            )

            # 提取并返回唯一书名列表
            buckets = response["aggregations"]["unique_books"]["buckets"]
            return [bucket["key"] for bucket in buckets if bucket["key"]]

        except Exception as e:
            print(f"❌ 获取书名列表失败: {str(e)}")
            return []  # 失败时返回空列表
    
    def count(self) -> int:
        """
        获取索引中的文档总数
        
        返回:
            int: 文档数量
        """
        try:
            result = self.client.count(index=self.index_name)
            return result.get("count", 0)
        except Exception as e:
            print(f"❌ 获取文档数量失败: {str(e)}")
            return 0
    
    def search_sparse(self, query: str, top_k: int = 5, book_filter: List[str] = None) -> List[Dict[str, Any]]:
        """
        使用稀疏向量方式进行搜索
        
        参数:
            query (str): 查询文本
            top_k (int): 返回结果数量
            book_filter (List[str]): 书籍名称过滤列表，只返回指定书籍中的内容
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            # 生成查询向量
            query_vec = self.sparse_embed_model.embed_query(query)

            # 确保我们有稀疏向量格式
            if not isinstance(query_vec, dict) or 'indices' not in query_vec or 'values' not in query_vec:
                print(f"⚠️ 查询嵌入生成错误")
                return []

            # 转换为ES稀疏向量格式
            sparse_query = {}
            for idx, val in zip(query_vec['indices'], query_vec['values']):
                sparse_query[str(idx)] = float(val)

            # 构建更简单的查询 - 使用文本匹配作为备选方案
            should_clauses = []

            # 添加summary匹配查询（原来是text字段）
            should_clauses.append({
                "match": {
                    "summary": {  # 修改为summary字段
                        "query": query,
                        "boost": 1.0
                    }
                }
            })

            # 使用简单的term查询来匹配向量中的关键维度
            # 选择权重最高的几个维度
            top_dims = sorted(sparse_query.items(), key=lambda x: x[1], reverse=True)[:10]
            for dim, weight in top_dims:
                should_clauses.append({
                    "term": {
                        f"vector_sparse.{dim}": {
                            "value": weight,
                            "boost": weight  # 使用权重作为boost值
                        }
                    }
                })

            # 构建查询基础部分
            query_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1
                    }
                },
                "_source": ["summary", "text", "is_image_description", "book_name"]  # 只使用存在的字段
            }
            
            # 如果指定了书籍过滤，添加过滤条件
            if book_filter and len(book_filter) > 0:
                print(f"应用Elasticsearch书籍过滤: {book_filter}")
                
                # 添加书籍过滤条件
                book_terms = {"terms": {"book_name": book_filter}}
                
                # 将过滤条件添加到查询中
                if "filter" not in query_body["query"]["bool"]:
                    query_body["query"]["bool"]["filter"] = []
                    
                query_body["query"]["bool"]["filter"].append(book_terms)

            # 执行搜索
            response = self.client.search(
                index=self.index_name,
                body=query_body
            )

            # 处理结果
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "summary": hit["_source"].get("summary", ""),
                    "text": hit["_source"].get("text", ""),
                    "book_name": hit["_source"].get("book_name", ""),
                    "is_image_description": hit["_source"].get("is_image_description", False)
                }
                results.append(result)

            return results

        except Exception as e:
            print(f"❌ 稀疏向量搜索失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []


