from qdrant_client import QdrantClient
from filter_extractor import extract_filter_conditions, to_qdrant_filter_python
from qdrant_search import search_qdrant, SearchConfig, flatten_points

client = QdrantClient(host="localhost", port=6333)
# query_text = "為了美化帳戶提供帳戶，成立加重詐欺的案件"
# query_text = "被告趙璧 擔任提款手 提領詐欺款項 臺灣高等法院臺中分院 113年度金上訴字第1464號"
# query_text = "有沒有被告在二審主張依詐欺犯罪危害防制條例第47條，可以減輕其刑，然後在洗錢防制部分應該適用舊法成功改判減輕的案例"
query_text = "有沒有被告是車手腳色 非提供帳戶的然後都不認罪 卻給予緩刑的詐欺案例"
structured_filter = extract_filter_conditions(query_text)
condition, reconstruct_question = to_qdrant_filter_python(structured_filter)

# print(structured_filter)
print("="*50)
print("------>>>  reconstruct_question: ", reconstruct_question)
print("="*50)
print("------>>>  condition: ", condition)
print("="*50)

config = SearchConfig(
    collection="judgment_cat_test",
    # query_text=reconstruct_question,
    query_text=query_text,
    filter = condition
)

resp = search_qdrant(client, config)

results = flatten_points(resp)

print(results)