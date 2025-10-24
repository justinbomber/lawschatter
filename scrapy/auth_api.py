from __future__ import annotations

"""入口腳本：封裝至 `scrapy.judicial_api` 的模組化實作。

使用方式：
- 一次性執行：python -m scrapy.judicial_api.main --mode once
- 以台灣時間 00:00–06:00 排程：python -m scrapy.judicial_api.main --mode schedule

帳號密碼請以環境變數提供：
- JUDICIAL_API_USER
- JUDICIAL_API_PASSWORD
"""

from .judicial_api.main import main


if __name__ == "__main__":
    main()