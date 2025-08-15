# lotto_updater.py — 合併舊資料，保留全部歷史
# -*- coding: utf-8 -*-
import time
import csv
from pathlib import Path

import pandas as pd

# 從整合版 utils.py 匯入（已實作為抓 3D 最新 8 期）
from utils import fetch_latest20_from_official

CSV_PATH = Path("data/3star_history.csv")

def _ensure_csv_header(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["date", "issue", "d1", "d2", "d3", "source", "updated_at"]
            )

def _load_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["date","issue","d1","d2","d3","source","updated_at"])
    df = pd.read_csv(path, encoding="utf-8")
    # 欄位齊一化
    for c in ["date","issue","d1","d2","d3","source","updated_at"]:
        if c not in df.columns:
            df[c] = "" if c in ["date","issue","source"] else None
    # 數字欄轉 int（容錯）
    for c in ["d1","d2","d3"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    return df[["date","issue","d1","d2","d3","source","updated_at"]]

def update_history_csv_from_web(csv_path: Path = CSV_PATH) -> int:
    """抓最新 8 期，與既有 CSV 合併後去重保存；回傳本次新增的筆數。"""
    # 1) 抓新資料（DataFrame: d1,d2,d3）
    df_new = fetch_latest20_from_official()
    if df_new is None or df_new.empty:
        raise RuntimeError("官網回傳為空，無法更新 CSV")

    # 2) 加上固定欄位
    now_ts = int(time.time())
    df_new = df_new.copy()
    for c in ["date","issue","source","updated_at"]:
        df_new[c] = ""
    df_new["source"] = "taiwanlottery"
    df_new["updated_at"] = now_ts

    # 欄位排序一致
    df_new = df_new[["date","issue","d1","d2","d3","source","updated_at"]]

    # 3) 讀舊資料並合併
    _ensure_csv_header(csv_path)
    df_old = _load_existing(csv_path)

    before_cnt = len(df_old)
    df_all = pd.concat([df_old, df_new], ignore_index=True)

    # 4) 去重策略：
    #    官網暫時沒有期別/日期 -> 以 (d1,d2,d3) 為鍵去重；若未來加上 issue/date 可改 keys
    df_all["key"] = df_all["d1"].astype(str) + df_all["d2"].astype(str) + df_all["d3"].astype(str)
    # 保留最新一筆（updated_at 較新）
    df_all.sort_values(["key","updated_at"], ascending=[True, False], inplace=True)
    df_all = df_all.drop_duplicates(subset=["key"], keep="first").drop(columns=["key"])

    # 5) 保存
    df_all.to_csv(csv_path, index=False, encoding="utf-8-sig")

    after_cnt = len(df_all)
    added = max(0, after_cnt - before_cnt)
    return added

def refresh_and_retrain_if_needed(retrain_fn=None) -> int:
    added = update_history_csv_from_web()
    if retrain_fn is not None:
        try:
            retrain_fn()
        except Exception as e:
            print(f"[WARN] retrain 失敗：{e}")
    return added

if __name__ == "__main__":
    n = update_history_csv_from_web()
    print(f"已新增 {n} 筆，並保留全部歷史。")
