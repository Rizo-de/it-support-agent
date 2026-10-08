from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openai/gpt-oss-20b"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Keine Nachricht erhalten"}), 400

    user_message = data["message"]

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an IT Support Assistant. Help users troubleshoot common computer and Windows problems clearly and safely."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }
    )

    if response.status_code != 200:
        return jsonify({
            "error": "OpenRouter Fehler",
            "details": response.text
        }), response.status_code

    result = response.json()

    answer = result["choices"][0]["message"]["content"]

    return jsonify({
        "answer": answer
    })


if __name__ == "__main__":
    app.run(debug=True)