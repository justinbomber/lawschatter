import hashlib
import logging
from ..domain import HashGenerator

logger = logging.getLogger(__name__)


class MD5HashGenerator(HashGenerator):
    
    def generate(self, unique_string: str) -> str:
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

