import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "embedding-seperate"

client = QdrantClient(url=QDRANT_URL)

all_point_ids = []
offset = None

while True:
    records, next_offset = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=100,
        offset=offset,
        with_payload=False,
        with_vectors=False
    )
    
    all_point_ids.extend([record.id for record in records])
    
    if next_offset is None:
        break
    offset = next_offset

if all_point_ids:
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.PointIdsList(points=all_point_ids)
    )


