import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from flask import Flask, request, jsonify
import tempfile, os, json, re

from chains.crop_chain import recommend_crop
from chains.soil_chain import analyze_soil
from chains.irrigation_chain import analyze_irrigation
from chains.disease_chain import analyze_leaf
from chains.qna_chain import krishimitra_answer

import warnings
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
API_KEY = os.getenv("KRISHIMITRA_API_KEY")

warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app)


@app.before_request
def verify_api_key():
    if request.path == "/":
        return
    client_key = request.headers.get("x-api-key") or request.args.get("api_key")
    if not client_key or client_key != API_KEY:
        return jsonify({"error": "Unauthorized — invalid or missing API key."}), 401



@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "🌾 KrishiMitra Unified Flask API is running successfully!",
        "endpoints": ["/krishimitra (POST)"],
        "note": "Include your x-api-key header in every request."
    })


@app.route("/krishimitra", methods=["POST"])
def krishimitra_api():
    """
    🔹 Single endpoint that automatically detects which AI chain to use:
      - Image → Disease detection
      - Query text → Q&A
      - city + crop + soil_type → Irrigation
      - crop + location → Soil
      - location + season → Crop
    """
    try:
        if "file" in request.files:
            file = request.files["file"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                file.save(tmp.name)
                result = analyze_leaf(tmp.name)
            os.remove(tmp.name)
            return jsonify({"module": "disease_chain", "result": result})

        data = request.get_json(silent=True) or request.form.to_dict()
        print("[DEBUG] Received:", data)

        if "query" in data:
            answer = krishimitra_answer(data["query"])
            return jsonify({"module": "qna_chain", "answer": answer})

        if all(k in data for k in ["city", "crop", "soil_type"]):
            result = analyze_irrigation(data)
            return jsonify({"module": "irrigation_chain", "result": result})

        if all(k in data for k in ["crop", "location"]):
            result = analyze_soil(data)
            return jsonify({"module": "soil_chain", "result": result})

        if all(k in data for k in ["location", "season"]):
            result = recommend_crop(data)
            return jsonify({"module": "crop_chain", "result": result})

        return jsonify({"error": "Invalid input — please provide a valid image, query, or structured data."})

    except Exception as e:
        print("[ERROR]", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)




