import jieba
jieba.set_dictionary("dict.txt.big")
def load_stopwords(path: str):
    with open(path, "r", encoding="utf-8") as f:
        stopwords = set(line.strip() for line in f if line.strip())
    return stopwords

if __name__=="__main__":
    # 要測試的10句話
    sentences = [
        "請你查一下今天台北天氣如何。",
        "他正在學習自然語言處理和機器學習。",
        "教育部長今天上午參加了立法院的質詢。",
        "他想了解蘋果手機的營養成分與健康影響。",
        "中華電信的5G資費方案很複雜，我不太懂。",
        "你玩神奇寶貝的時候，有打過道館嗎?"
    ]
    stopwords = load_stopwords("zh-t.txt")
    for sentence in sentences:
        words = [t.strip() for t in jieba.cut(sentence, cut_all=False, HMM=True) if t.strip() and t.strip() not in stopwords]
        print(f"原句: {sentence}")
        print(f"斷詞結果: {words}")
        print("-" * 40)