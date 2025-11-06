import json
import logging
import os
from pathlib import Path
from typing import List
from ..domain import (
    JudgmentRepository,
    JudgmentRecord,
    SummaryExtractor,
    SummaryExtractionResult,
    SchemaProvider,
)

logger = logging.getLogger(__name__)


class ExportJudgmentSummaryToJsonUseCase:
    
    def __init__(
        self,
        judgment_repo: JudgmentRepository,
        extractor: SummaryExtractor,
        schema_provider: SchemaProvider,
        output_dir: str = "output"
    ):
        self.judgment_repo = judgment_repo
        self.extractor = extractor
        self.schema_provider = schema_provider
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"確認輸出目錄存在: {self.output_dir}")
    
    def execute(self, jids: List[str]) -> int:
        logger.info(f"開始匯出判決 summary 為 JSON 檔案，共 {len(jids)} 筆")
        
        exported_count = 0
        for jid in jids:
            if self._export_judgment_summary(jid):
                exported_count += 1
        
        logger.info(f"匯出完成，成功處理 {exported_count} 筆判決")
        return exported_count
    
    def _export_judgment_summary(self, jid: str) -> bool:
        logger.info(f"匯出判決 summary: {jid}")
        
        judgment = self.judgment_repo.get_judgment(jid)
        
        logger.info(f"開始提取 summary: {jid}")
        schema = self.schema_provider.get_schema()
        extraction_result = self.extractor.extract(judgment, schema)
        
        judgment_dict = self._convert_to_dict(judgment, extraction_result)
        
        output_path = self._get_output_path(jid)
        self._save_to_json(judgment_dict, output_path)
        
        logger.info(f"成功匯出判決 summary 至: {output_path}")
        return True
    
    def _convert_to_dict(
        self, 
        judgment: JudgmentRecord, 
        extraction: SummaryExtractionResult
    ) -> dict:
        defendants_list = []
        for defendant in extraction.defendants:
            defendants_list.append({
                "name": defendant.name,
                "role": defendant.role,
                "A_fact": defendant.A_fact,
                "B_claim": defendant.B_claim,
                "C_court_finding": defendant.C_court_finding,
                "D_court_reason": defendant.D_court_reason,
                "E_legal_eval": defendant.E_legal_eval,
            })
        
        return {
            "jid": judgment.jid,
            # "jid_full": judgment.jid_full,
            # "jyear": judgment.jyear,
            # "jcase": judgment.jcase,
            # "jno": judgment.jno,
            # "jdate": judgment.jdate,
            # "jtitle": judgment.jtitle,
            # "case_type": judgment.case_type,
            # "jtitle_type": judgment.jtitle_type,
            # "jfull": judgment.jfull,
            "case_fact_summary": extraction.case_fact_summary,
            "defendants": defendants_list,
            "case_highlights": extraction.case_highlights,
        }
    
    def _get_output_path(self, jid: str) -> str:
        filename = f"{jid}_summary.json"
        return os.path.join(self.output_dir, filename)
    
    def _save_to_json(self, data: dict, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

