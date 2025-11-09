# Chunk 策略說明

## 文件層級設計

| 層級                         | 說明                           | 文件數量    | 用途                       | 組成的摘要類型 (`summary_type`)                                                                                                                                       |
| ---------------------------- | ------------------------------ | ----------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **案件層 (case)**      | 整體案件事實與主要爭點         | 每案 1 份   | 查全案重點、法院整體見解   | `case_fact_summary`（案件事實）`case_highlights`（案件重點）                                                                                                   |
| **被告層 (defendant)** | 單一被告的行為、主張與裁判理由 | 每被告 1 份 | 查個別被告的量刑、法院認定 | `role`（角色）`A_fact`（事實）`B_claim`（主張）`C_court_finding`（法院認定）`D_court_reason`（法院理由）`E_legal_eval`（法律評估） |

---

## 設計重點

* **被告層合併為單一文件** ：

  平均長度約 1000–1800 字，語意仍完整。

  若拆分為多個段落，檢索結果易失去上下文。

* **`doc_level` 用於區分文件層級（`case` / `defendant`）** ：

  建立嵌入與查詢時，可依此欄位直接過濾來源，

  避免案件摘要與被告摘要同時被檢索到。

  例如：使用者只想查全案爭點時，可設定 `doc_level = 'case'`。

* **被告層的 `defendants` 欄位僅保留當前被告資料** ：

  一份判決可能包含多名被告，若每份文件都保留完整 defendants 清單，

  查詢條件（如「刑期五個月」、「有沒收物」）可能跨被告誤匹配：

* 被告 A 有五個月刑期
* 被告 B 有沒收物

  → 若兩者同在一份文件中，檢索引擎可能誤以為「同一人符合兩條件」。

  因此每份被告層文件僅保留該被告自身資訊，

  讓 metadata 過濾與語義檢索都能精確對應。

---

## JSON 範例

**案件層**

<pre class="overflow-visible!" data-start="1061" data-end="1282"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"jid"</span><span>:</span><span></span><span>"COURT,114,簡上,121,20250630,1"</span><span>,</span><span>
  </span><span>"doc_level"</span><span>:</span><span></span><span>"case"</span><span>,</span><span>
  </span><span>"case_metadata"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"case_type"</span><span>:</span><span></span><span>"刑法"</span><span>,</span><span>
    </span><span>"jtitle_type"</span><span>:</span><span></span><span>"詐欺"</span><span>,</span><span>
    </span><span>"second_instance"</span><span>:</span><span></span><span>true</span><span>
  </span><span>}</span><span>,</span><span>
  </span><span>"page_content"</span><span>:</span><span></span><span>"案件事實: ...\n案件重點: ..."</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

**被告層**

<pre class="overflow-visible!" data-start="1293" data-end="1683"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"jid"</span><span>:</span><span></span><span>"COURT,114,簡上,121,20250630,1"</span><span>,</span><span>
  </span><span>"doc_level"</span><span>:</span><span></span><span>"defendant"</span><span>,</span><span>
  </span><span>"defendants"</span><span>:</span><span></span><span>[</span><span>
    </span><span>{</span><span>
      </span><span>"fixed_term_months"</span><span>:</span><span></span><span>5</span><span>,</span><span>
      </span><span>"is_second_instance"</span><span>:</span><span></span><span>true</span><span></span><span>,</span><span>
      </span><span>"has_confiscated_items"</span><span>:</span><span></span><span>true</span><span></span><span>,</span><span>
      </span><span>"violated_law_articles"</span><span>:</span><span></span><span>[</span><span>
        </span><span>"刑法第339條之4第2項、第1項第2款"</span><span>,</span><span>
        </span><span>"刑法第25條第2項"</span><span>
      </span><span>]</span><span>
    </span><span>}</span><span>
  </span><span>]</span><span>,</span><span>
  </span><span>"page_content"</span><span>:</span><span></span><span>"角色: ...\n事實: ...\n主張: ...\n法院認定: ...\n法院理由: ...\n法律評估: ..."</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

## 查詢與擴充建議

* 檢索時可依 `doc_level` 過濾文件層級。
* 若後續需支援從摘要回溯原判決，可在 metadata 中加入：

  <pre class="overflow-visible!" data-start="1770" data-end="1859"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>"parent_jid"</span><span>:</span><span></span><span>"COURT,114,簡上,121,20250630,1"</span><span>,</span><span>
  </span><span>"parent_type"</span><span>:</span><span></span><span>"full_text"</span><span>
  </span></span></code></div></div></pre>

  以建立摘要與原文的關聯。
