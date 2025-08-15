# utils.py (CONSOLIDATED) – keeps GUI functions and 3D last-8 fetch
import os, sys, re
import pandas as pd
import numpy as np
from datetime import datetime

# ---------- paths ----------
def _base_path():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def _csv_path():
    return os.path.join(_base_path(), "data", "3star_history.csv")

def load_history():
    path = _csv_path()
    df = pd.read_csv(path, encoding="utf-8-sig")
    if {"d1","d2","d3"}.issubset(df.columns):
        cols = ["d1","d2","d3"]
    elif {"號碼1","號碼2","號碼3"}.issubset(df.columns):
        df = df.rename(columns={"號碼1":"d1","號碼2":"d2","號碼3":"d3"}); cols = ["d1","d2","d3"]
    else:
        raise ValueError("CSV 需要欄位 d1,d2,d3（或 號碼1,號碼2,號碼3）")
    df = df[cols].dropna().astype(int)
    df = df[(df.d1.between(0,9))&(df.d2.between(0,9))&(df.d3.between(0,9))]
    return df

def pick_window(df: pd.DataFrame, key: str) -> pd.DataFrame:
    key = (key or "").strip()
    if key == "近10期": return df.tail(10)
    if key == "近50期": return df.tail(50)
    if key == "近100期": return df.tail(100)
    return df

# ---------- prediction buckets ----------
def _bucketize_counts(series: pd.Series):
    counts = series.value_counts().reindex(range(10), fill_value=0).sort_values(ascending=False)
    order = counts.index.tolist()
    hot = order[:3]; cold = order[-3:]; mid = [n for n in order if n not in hot and n not in cold]
    def bucket_weights(nums):
        if not nums: return {}
        vals = counts.loc[nums].astype(float)
        if vals.sum()==0: return {n: 1.0/len(nums) for n in nums}
        return (vals/vals.sum()).to_dict()
    return set(hot), set(mid), set(cold), bucket_weights(hot), bucket_weights(mid), bucket_weights(cold)

def _mix_distribution(hot_w, mid_w, cold_w, mix_ratio):
    final = {n:0.0 for n in range(10)}
    for n in final:
        if n in hot_w: final[n]+=mix_ratio.get("hot",0.0)*hot_w[n]
        if n in mid_w: final[n]+=mix_ratio.get("mid",0.0)*mid_w[n]
        if n in cold_w: final[n]+=mix_ratio.get("cold",0.0)*cold_w[n]
    s=sum(final.values())
    return {n:(0.1 if s<=0 else final[n]/s) for n in final}

def _sample_from_dist(dist):
    nums=np.array(list(dist.keys())); probs=np.array(list(dist.values()),dtype=float)
    probs=np.clip(probs,0,None); s=probs.sum(); probs=(np.ones_like(probs)/len(probs)) if s<=0 else (probs/s)
    return int(np.random.choice(nums,p=probs))

# ---------- GUI-required API ----------
def generate_predictions(window_key: str, num_sets:int=5):
    df=load_history(); dfw=pick_window(df,window_key)
    all_nums=pd.concat([dfw["d1"],dfw["d2"],dfw["d3"]],ignore_index=True)
    hot,mid,cold,hot_w,mid_w,cold_w=_bucketize_counts(all_nums)
    pos1={"hot":0.45,"mid":0.35,"cold":0.20}; pos2=pos1; pos3={"hot":0.20,"mid":0.35,"cold":0.45}
    d1=_mix_distribution(hot_w,mid_w,cold_w,pos1); d2=_mix_distribution(hot_w,mid_w,cold_w,pos2); d3=_mix_distribution(hot_w,mid_w,cold_w,pos3)
    return [[_sample_from_dist(d1),_sample_from_dist(d2),_sample_from_dist(d3)] for _ in range(num_sets)]

def computer_pick_all():
    return generate_predictions("全部",1)[0]

# ---------- fetch latest (3D last-8) ----------
def fetch_latest20_from_official(timeout=20):
    """
    New site often shows only a small recent window.
    This function collects the last 8 draws of 3D (三星彩) by trying several 3D pages
    and parsing text or <img> digits.
    Returns: DataFrame with columns ['d1','d2','d3']
    """
    import requests, re
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    BASES = [
        "https://www.taiwanlottery.com/lotto/3D/history",
        "https://www.taiwanlottery.com/lotto/3d/history",
        "https://www.taiwanlottery.com/lotto/3D",
        "https://www.taiwanlottery.com/lotto/3d",
        "https://www.taiwanlottery.com/",
    ]

    def parse_rows(html):
        soup = BeautifulSoup(html, "lxml")
        rows = []
        img_digit = re.compile(r'([0-9])(?=\.(?:png|gif|jpg|jpeg|webp))', re.I)
        # table style
        for tr in soup.select("table tr"):
            digits = []
            for td in tr.find_all("td"):
                txt = (td.get_text(strip=True) or "")
                if len(txt)==1 and txt.isdigit():
                    digits.append(int(txt))
                else:
                    for img in td.find_all("img"):
                        alt = (img.get("alt") or "").strip()
                        if len(alt)==1 and alt.isdigit():
                            digits.append(int(alt)); continue
                        src = img.get("src") or ""
                        m = img_digit.search(src)
                        if m: digits.append(int(m.group(1)))
                if len(digits)>=3: break
            if len(digits)>=3:
                rows.append((digits[0],digits[1],digits[2]))
        # fallback blocks
        if not rows:
            for box in soup.select("[class*=ball], [class*=num], [class*=number], [class*=win], [class*=result]"):
                digits=[int(x) for x in re.findall(r'(?<!\\d)[0-9](?!\\d)', box.get_text(' ', strip=True))]
                for i in range(0,len(digits)-2,3):
                    rows.append((digits[i],digits[i+1],digits[i+2]))
        # generic fallback
        if not rows:
            digits=[int(x) for x in re.findall(r'(?<!\\d)[0-9](?!\\d)', soup.get_text(' ', strip=True))]
            for i in range(0,len(digits)-2,3):
                rows.append((digits[i],digits[i+1],digits[i+2]))
        return rows[-8:] if len(rows)>=8 else rows

    s = requests.Session(); s.verify=False
    s.headers.update({"User-Agent":"Mozilla/5.0"})
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=1, backoff_factor=0.5,
                                                     status_forcelist=[429,500,502,503,504], raise_on_status=False)))

    last_err=None
    for base in BASES:
        for url in (base, base.replace("https://","http://",1)):
            try:
                r = s.get(url, timeout=timeout, allow_redirects=True); r.raise_for_status()
                rows = parse_rows(r.text)
                if rows:
                    df = pd.DataFrame(rows, columns=["d1","d2","d3"])
                    df = df[(df.d1.between(0,9))&(df.d2.between(0,9))&(df.d3.between(0,9))]
                    return df.reset_index(drop=True)
            except Exception as e:
                last_err=e; continue
    raise RuntimeError(f"官網資料解析失敗（3D）。最後錯誤：{last_err}")

# ---------- outputs ----------
def _report_dir():
    out_dir=os.path.join(os.getcwd(),"report"); os.makedirs(out_dir,exist_ok=True); return out_dir

def save_predictions_to_csv(predictions, output_dir="report"):
    out=os.path.join(os.getcwd(),output_dir); os.makedirs(out,exist_ok=True)
    df=pd.DataFrame(predictions,columns=["Number1","Number2","Number3"])
    df.to_csv(os.path.join(out,"predicted_sets.csv"),index=False,encoding="utf-8-sig")

def generate_html_report(predictions, window_key: str, output_dir="report"):
    out=os.path.join(os.getcwd(),output_dir); os.makedirs(out,exist_ok=True)
    fname=datetime.now().strftime("%Y%m%d_%H%M%S")+".html"
    path=os.path.join(out,fname)
    html=["<html><head><meta charset='utf-8'><title>預測報表</title></head><body>",
          f"<h1>預測結果（區間：{window_key}）</h1>","<ol>"]
    for i,p in enumerate(predictions,1):
        html.append(f"<li>第 {i} 組：{p[0]}、{p[1]}、{p[2]}</li>")
    html+=["</ol>","</body></html>"]
    open(path,"w",encoding="utf-8").write("\\n".join(html))
