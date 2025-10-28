import logging
from ..domain import JudgmentFilter, JudgmentRecord

logger = logging.getLogger(__name__)


class AdjudicateJudgmentFilter(JudgmentFilter):
    
    def should_ignore(self, judgment: JudgmentRecord) -> bool:
        if not judgment.jfull:
            logger.info(f"判決 {judgment.jid} 無 jfull 欄位，不過濾")
            return False
        
        first_20_chars = judgment.jfull[:20]
        if "裁定" in first_20_chars:
            logger.info(f"判決 {judgment.jid} 前20字包含「裁定」，過濾")
            return True

        return False

