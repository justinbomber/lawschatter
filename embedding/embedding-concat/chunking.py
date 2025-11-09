import os
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.documents import Document
from uuid import uuid4
from supabase import create_client

# from hybrid_embed import get_qdrant_hybrid_vector_store

load_dotenv()


@dataclass
class JudgmentSummary:
    point_id: str
    jid: str
    jdate: str
    summary_type: str
    content: str
    defendent_name: Optional[str] = None


@dataclass
class JudgmentMetadata:
    jid: str
    jid_full: str
    jyear: str
    jcase: str
    jno: str
    jdate: str
    jtitle: str
    case_type: str
    defendants: List[Dict[str, Any]]
    case_metadata: Dict[str, Any]


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be provided in the environment.")

client = create_client(SUPABASE_URL, SUPABASE_KEY)
schema_name: str = "lawschatter"

CASE_LEVEL_TYPES = {"case_fact_summary": "案件事實", "case_highlights": "案件重點"}
DEFENDANT_LEVEL_TYPES = {
    "role": "角色",
    "A_fact": "事實",
    "B_claim": "主張",
    "C_court_finding": "法院認定",
    "D_court_reason": "法院理由",
    "E_legal_eval": "法律評估",
}
case_summaries_order = {k: i for i, k in enumerate(CASE_LEVEL_TYPES.keys())}
defendant_summaries_order = {k: i for i, k in enumerate(DEFENDANT_LEVEL_TYPES.keys())}

def enqueue_document(
    documents: List[Document],
    content: str,
    metadata_dict: Dict[str, Any],
) -> None:
    content = content.strip()
    if not content:
        return
    documents.append(Document(page_content=content, metadata=metadata_dict))


# vector_store = get_qdrant_hybrid_vector_store()


resp = client.rpc("get_unembedded_jids_2").execute()
result = resp.data if resp.data else []
jids = [row["jid"] for row in result]

if not jids:
    print("No unembedded JIDs returned by RPC `get_unembedded_jids_2`.")


for jid in jids:
    case_summaries: List[JudgmentSummary] = []
    defendant_summaries: Dict[str, List[JudgmentSummary]] = defaultdict(list)
    documents: List[Document] = []
    document_ids: List[str] = []

    resp = (
        client.schema(schema_name)
        .table("judgment_metadata")
        .select("*")
        .eq("jid", jid)
        .execute()
    )
    
    if not resp.data:
        raise ValueError(f"No metadata found for jid={jid}")

    row = resp.data[0]
    metadata = JudgmentMetadata(
        jid=row["jid"],
        jid_full=row["jid_full"],
        jyear=row["jyear"],
        jcase=row["jcase"],
        jno=row["jno"],
        jdate=row["jdate"],
        jtitle=row["jtitle"],
        case_type=row.get("case_type", ""),
        defendants=row.get("defendants", []),
        case_metadata=row.get("case_metadata", {}),
    )


    summary_resp = (
        client.schema(schema_name)
        .table("judgment_summary")
        .select("*")
        .eq("jid", jid)
        .execute()
    )

    summary_rows = summary_resp.data or []
    if not summary_rows:
        print(f"No summaries found for JID {jid}, skipping.")
        continue

    for row in summary_rows:
        summary = JudgmentSummary(
            point_id=row["point_id"],
            jid=row["jid"],
            jdate=row["jdate"],
            summary_type=row["summary_type"],
            content=row["content"],
            defendent_name=row.get("defendent_name"),
        )

        if summary.summary_type in CASE_LEVEL_TYPES:
            case_summaries.append(summary)
        elif summary.summary_type in DEFENDANT_LEVEL_TYPES:
            if summary.defendent_name is None:
                raise ValueError(f"Defendant-level summary missing defendent_name: {summary}")
            defendant_summaries[summary.defendent_name].append(summary)
        else:
            raise ValueError(f"Unknown summary type: {summary.summary_type}")

    for defendant, summaries in defendant_summaries.items():
        ordered_summaries = sorted(
            summaries,
            key=lambda x: defendant_summaries_order.get(x.summary_type, 999),
        )
        content_lines = [
            f"{DEFENDANT_LEVEL_TYPES[summary.summary_type]}: {summary.content}"
            for summary in ordered_summaries
        ]
        content = "\n".join(content_lines).strip()

        base_metadata = asdict(metadata)
        focus_defendant_info = next(
            (d for d in metadata.defendants if d.get("defendant_name") == defendant),
            None,
        )
        if focus_defendant_info:
            base_metadata["defendants"] = [focus_defendant_info]

        base_metadata["doc_level"] = "defendant"

        enqueue_document(documents, content, base_metadata)
        print(f"Enqueued document for JID {jid}, defendant {defendant}")

    case_content_parts = []
    ordered_case_summaries = sorted(
        case_summaries,
        key=lambda x: case_summaries_order.get(x.summary_type, 999),
    )
    for summary in ordered_case_summaries:
        label = CASE_LEVEL_TYPES[summary.summary_type]
        case_content_parts.append(f"{label}: {summary.content}")

    case_content = "\n".join(case_content_parts).strip()
    case_metadata = asdict(metadata)
    case_metadata["doc_level"] = "case"


    enqueue_document(documents, case_content, case_metadata)
    print(f"Enqueued document for JID {jid}, case level")

    if not documents:
        print(f"No documents generated for JID {jid}")
        continue
    
    uuids = [str(uuid4()) for _ in range(len(documents))]
    # vector_store.add_documents(documents=documents, ids=uuids)
    print(f"Inserted {len(documents)} documents into Qdrant for JID {jid}")


