import os
import sys
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from .db_settings import (
    ELASTICSEARCH_URI,
    ELASTICSEARCH_USER,
    ELASTICSEARCH_PASSWORD,
    ELASTICSEARCH_INDEX,
    BGE_M3_MODEL_PATH,
    DENSE_VECTOR_DIMENSION,
    SPLADE_MODEL_PATH,
    SPARSE_VECTOR_DIMENSION
)
from .vector_encoder import BgeM3Embedding, SpladeEmbedding
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
    支持 BM25 稀疏检索 + bge-m3 稠密向量检索
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
        self.uri = uri
        self.user = user
        self.password = password
        self.index_name = index_name

        print(f"🔌 连接到Elasticsearch: {self.uri}")
        try:
            if self.user and self.password:
                self.client = Elasticsearch(
                    [self.uri],
                    basic_auth=(self.user, self.password),
                    verify_certs=False
                )
            else:
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

    def get_all_source_names(self) -> List[str]:
        """
        获取索引中所有唯一的知识库来源名称

        返回:
            List[str]: 所有唯一的来源名称列表
        """
        try:
            query_body = {
                "size": 0,
                "aggs": {
                    "unique_sources": {
                        "terms": {
                            "field": "book_name",
                            "size": 10000
                        }
                    }
                }
            }

            response = self.client.search(
                index=self.index_name,
                body=query_body
            )

            buckets = response["aggregations"]["unique_sources"]["buckets"]
            return [bucket["key"] for bucket in buckets if bucket["key"]]

        except Exception as e:
            print(f"❌ 获取知识库来源列表失败: {str(e)}")
            return []
    
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
        使用稀疏向量方式进行搜索（BM25 + SPLADE）
        
        参数:
            query (str): 查询文本
            top_k (int): 返回结果数量
            book_filter (List[str]): 知识库来源过滤列表
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            # 生成查询向量
            query_vec = self.sparse_embed_model.embed_query(query)

            if not isinstance(query_vec, dict) or 'indices' not in query_vec or 'values' not in query_vec:
                print(f"⚠️ 查询嵌入生成错误")
                return []

            # 转换为ES稀疏向量格式
            sparse_query = {}
            for idx, val in zip(query_vec['indices'], query_vec['values']):
                sparse_query[str(idx)] = float(val)

            should_clauses = []

            # 添加summary匹配查询（BM25）
            should_clauses.append({
                "match": {
                    "summary": {
                        "query": query,
                        "boost": 1.0
                    }
                }
            })

            # 使用SPLADE稀疏向量
            top_dims = sorted(sparse_query.items(), key=lambda x: x[1], reverse=True)[:10]
            for dim, weight in top_dims:
                should_clauses.append({
                    "term": {
                        f"vector_sparse.{dim}": {
                            "value": weight,
                            "boost": weight
                        }
                    }
                })

            query_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1
                    }
                },
                "_source": ["summary", "text", "is_image_description", "book_name"]
            }
            
            # 知识库来源过滤
            if book_filter and len(book_filter) > 0:
                print(f"应用知识库来源过滤: {book_filter}")
                book_terms = {"terms": {"book_name": book_filter}}
                if "filter" not in query_body["query"]["bool"]:
                    query_body["query"]["bool"]["filter"] = []
                query_body["query"]["bool"]["filter"].append(book_terms)

            response = self.client.search(
                index=self.index_name,
                body=query_body
            )

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
