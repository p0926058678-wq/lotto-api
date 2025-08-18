import random

def generate_predictions():
    predictions = []
    for _ in range(5):  # 產出 5 組預測號碼
        prediction = [random.randint(0, 9) for _ in range(3)]
        predictions.append(prediction)
    return {"predictions": predictions}

def computer_pick_all():
    picks = []
    for _ in range(10):  # 電腦選 10 組號碼
        pick = [random.randint(0, 9) for _ in range(3)]
        picks.append(pick)
    return {"computer_picks": picks}
# 請將原 utils.py 程式碼貼上這裡
