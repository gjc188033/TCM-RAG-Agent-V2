from ..embeddings import QwenEmbedding
if __name__ == '__main__':
    reference = "我喜欢吃苹果"
    sample1 = "我不喜欢吃苹果"
    sample2 = "我很喜欢吃苹果"

    em=QwenEmbedding()
    reference_embedding = em.embed_query(reference)
    sample1_embedding = em.embed_query(sample1)
    sample2_embedding = em.embed_query(sample2)
    score1 = em.normalize_embedding(reference_embedding).dot(em.normalize_embedding(sample1_embedding))
    score2 = em.normalize_embedding(reference_embedding).dot(em.normalize_embedding(sample2_embedding))
    print("样例1（我不喜欢吃苹果） → 嵌入相似度:", score1)
    print("样例2（我很喜欢吃苹果） → 嵌入相似度:", score2)