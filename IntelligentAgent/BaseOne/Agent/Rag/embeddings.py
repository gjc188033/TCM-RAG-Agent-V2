import sys
import os
import torch
import numpy as np
from transformers import PretrainedConfig
from typing import List, Dict, Union, Any
import logging
from .config import (QWEN_MODEL_PATH, DENSE_VECTOR_DIMENSION, SPLADE_MODEL_PATH, SPARSE_VECTOR_DIMENSION)
from tqdm import tqdm

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QwenEmbedding:
    """
    Qwen模型嵌入封装类
    使用本地Qwen模型生成文本向量
    """

    def __init__(self, model_path=QWEN_MODEL_PATH, target_dim=DENSE_VECTOR_DIMENSION):
        """
        初始化Qwen嵌入模型
        
        参数:
            model_path: Qwen模型路径
            target_dim: 目标向量维度
        """
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 直接使用路径加载
        print(f"正在加载Qwen嵌入模型，路径: {model_path}")
        
        try:
            # 使用transformers直接加载模型
            from transformers import AutoModel, AutoTokenizer
            import os
            
            print("开始加载分词器...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            print("✓ 分词器加载完成")
            
            print("开始加载模型...")
            # 使用CPU加载模型，避免CUDA相关问题
            os.environ["CUDA_VISIBLE_DEVICES"] = ""  # 临时禁用CUDA
            self.model = AutoModel.from_pretrained(
                model_path,
                trust_remote_code=True
            )
            # 加载完成后，如果可用则移动到GPU
            if torch.cuda.is_available():
                os.environ.pop("CUDA_VISIBLE_DEVICES", None)  # 恢复CUDA可见性
                self.device = "cuda"
                self.model = self.model.to(self.device)
            print("✓ 模型加载完成")
            
            # 模型放入评估模式
            self.model.eval()
            
            # 获取模型维度
            self.model_dim = self.model.config.hidden_size
            print(f"✅ Qwen嵌入模型加载完成，运行设备: {self.device}")
            print(f"✅ 模型原始维度: {self.model_dim}")
            
        except Exception as e:
            print(f"加载模型时出错: {e}")
            raise e

        # 根据配置设置目标维度
        self.target_dim = self.model_dim
        if target_dim != self.model_dim:
            print(f"⚠️ 配置的向量维度({target_dim})与模型原始维度({self.model_dim})不一致")
            print(f"⚠️ 将使用模型原始维度: {self.model_dim}")

    def normalize_embedding(self, embedding):
        """对嵌入向量进行L2归一化"""
        return embedding / np.linalg.norm(embedding)

    def _get_embedding(self, text: str) -> list:
        """获取文本的嵌入向量"""
        with torch.no_grad():
            # 对文本进行编码
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to(
                self.device)

            # 获取模型输出
            outputs = self.model(**inputs)

            # 使用CLS标记作为句子表示
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

            # 归一化并返回列表
            return self.normalize_embedding(embedding).tolist()

    def embed_query(self, text: str) -> list:
        """
        将单条查询文本转换为向量
        
        参数:
            text: 输入文本
            
        返回:
            嵌入向量
        """
        return self._get_embedding(text)

    def embed_documents(self, texts: list) -> list:
        """
        将多条文本转换为向量
        
        参数:
            texts: 输入文本列表
            
        返回:
            嵌入向量列表
        """
        results = []
        for text in texts:
            results.append(self._get_embedding(text))
        return results


class SpladeEmbedding:
    """
    SPLADE模型嵌入封装类
    使用SPLADE模型生成稀疏文本向量
    """

    def __init__(self, model_path=SPLADE_MODEL_PATH):
        """
        初始化SPLADE嵌入模型
        
        参数:
            model_path: SPLADE模型路径
        """
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 直接使用路径加载
        print(f"正在加载SPLADE嵌入模型，路径: {model_path}")
        
        try:
            # 使用transformers直接加载模型
            from transformers import AutoModelForMaskedLM, AutoTokenizer
            import os
            
            print("开始加载SPLADE分词器...")
            # 使用本地文件加载，避免网络请求
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True
            )
            print("✓ SPLADE分词器加载完成")
            
            print("开始加载SPLADE模型...")
            # 使用CPU加载模型，避免CUDA相关问题
            os.environ["CUDA_VISIBLE_DEVICES"] = ""  # 临时禁用CUDA
            self.model = AutoModelForMaskedLM.from_pretrained(
                model_path,
                local_files_only=True
            )
            # 加载完成后，如果可用则移动到GPU
            if torch.cuda.is_available():
                os.environ.pop("CUDA_VISIBLE_DEVICES", None)  # 恢复CUDA可见性
                self.device = "cuda"
                self.model = self.model.to(self.device)
            print(f"✓ SPLADE模型加载完成，运行设备: {self.device}")
            
            # 模型放入评估模式
            self.model.eval()
            
            print(f"✅ SPLADE嵌入模型加载完成")
            print(f"✅ 词汇表大小: {len(self.tokenizer.get_vocab())}")
            
        except Exception as e:
            print(f"加载SPLADE模型时出错: {e}")
            raise e

    def _get_sparse_embedding(self, text: str) -> Dict[str, List]:
        """
        获取文本的SPLADE稀疏嵌入向量
        
        返回:
            包含indices和values的字典
        """
        try:
            with torch.no_grad():
                # 对文本进行编码
                encoded_input = self.tokenizer(
                    text, 
                    return_tensors="pt", 
                    padding=True, 
                    truncation=True, 
                    max_length=512
                )
                
                # 将输入移动到模型所在的设备
                encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
                
                # 获取模型输出
                outputs = self.model(**encoded_input)
                
                # 获取词表大小的logits
                logits = outputs.logits[0]  # [seq_len, vocab_size]
                
                # 应用SPLADE激活: log(1 + ReLU(logits))
                relu = torch.nn.ReLU()
                activations = torch.log(1 + relu(logits))  # [seq_len, vocab_size]
                
                # 对所有token位置进行max pooling
                sparse_weights = torch.max(activations, dim=0)[0]  # [vocab_size]
                
                # 提取非零元素
                non_zero_mask = sparse_weights > 0.01  # 使用阈值过滤小权重
                non_zero_indices = torch.nonzero(non_zero_mask).squeeze().cpu().numpy()
                
                # 如果没有非零元素或者结果是标量，处理特殊情况
                if non_zero_indices.size == 0:
                    return {"indices": [], "values": []}
                
                # 确保indices是一维数组
                if non_zero_indices.ndim == 0:
                    non_zero_indices = np.array([non_zero_indices.item()])
                
                # 获取对应的权重值
                non_zero_values = sparse_weights[non_zero_indices].cpu().numpy()
                
                # 返回稀疏向量格式
                return {
                    "indices": non_zero_indices.tolist(),
                    "values": non_zero_values.tolist()
                }
        except Exception as e:
            print(f"生成稀疏向量时出错: {str(e)}")
            # 返回空向量作为回退方案
            return {"indices": [], "values": []}

    def embed_query(self, text: str) -> Dict[str, List]:
        """
        将单条查询文本转换为SPLADE稀疏向量
        
        参数:
            text: 输入文本
            
        返回:
            包含indices和values的稀疏向量字典
        """
        return self._get_sparse_embedding(text)

    def embed_documents(self, texts: list) -> List[Dict[str, List]]:
        """
        将多条文本转换为SPLADE稀疏向量
        
        参数:
            texts: 输入文本列表
            
        返回:
            稀疏向量字典列表
        """
        results = []
        for text in tqdm(texts, desc="SPLADE嵌入"):
            results.append(self._get_sparse_embedding(text))
        return results
