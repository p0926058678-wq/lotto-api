from flask import Flask, jsonify, request
from utils import generate_predictions, computer_pick_all
from lotto_updater import update_and_get_data
import os

app = Flask(__name__)

@app.route('/api/predict', methods=['GET'])
def predict():
    try:
        predictions = generate_predictions()
        return jsonify(predictions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pick_all', methods=['GET'])
def pick_all():
    picks = computer_pick_all()
    return jsonify(picks)

@app.route('/api/update', methods=['POST'])
def update_data():
    updated = update_and_get_data()
    return jsonify({"message": "Data updated", "updated_count": updated})

@app.route('/')
def home():
    return "🎯 Welcome to 3-Star Lotto API Server"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
