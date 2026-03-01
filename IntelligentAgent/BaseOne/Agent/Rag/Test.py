from .ElasticsearchWoker import ElasticsearchDB
from .MilvusWoker import MilvusDB
if __name__ == '__main__':
    Mw=MilvusDB()
    EW=ElasticsearchDB()

    # 获取搜索结果
    milvus_results = Mw.Find_Information("鲫鱼", top_k=5)
    es_results = EW.search_sparse("鲫鱼", top_k=5)
    
    # 打印Milvus结果
    print("Milvus结果:")
    print(type(milvus_results))  # 打印结果类型
    print(milvus_results)        # 打印整个结果
    
    # 打印Elasticsearch结果
    print("\nElasticsearch结果:")
    print(type(es_results))     # 打印结果类型
    for i, result in enumerate(es_results):
        print(f"\n结果 #{i+1}:")
        print(f"分数: {result.get('score', 0)}")
        print(f"摘要: {result.get('summary', '')[:100]}...")  # 只打印前100个字符
        print(f"书名: {result.get('book_name', '未知')}")





