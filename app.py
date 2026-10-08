from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openai/gpt-oss-20b"

SUPPORT_DATA_FILE = "support_data.json"


def load_support_data():
    try:
        with open(SUPPORT_DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        return []

    except json.JSONDecodeError:
        return []


def find_support_cases(user_message):
    support_data = load_support_data()

    message = user_message.lower()

    matches = []

    for case in support_data:

        score = 0

        problem = case.get("problem", "").lower()

        if problem and problem in message:
            score += 5

        for keyword in case.get("keywords", []):

            if keyword.lower() in message:
                score += 3

        if score > 0:
            matches.append({
                "score": score,
                "case": case
            })

    matches.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return [
        item["case"]
        for item in matches[:3]
    ]


SYSTEM_PROMPT = """
Du bist ein professioneller 1st-Level IT-Support-Agent.

Dein Ziel ist es, IT-Probleme schnell und strukturiert zu lösen.

Du hast Zugriff auf eine interne IT-Support-Wissensdatenbank.

Wenn passende Informationen aus der Wissensdatenbank vorhanden sind,
verwende diese Informationen bevorzugt.

WICHTIG:

Du bist KEIN Fragebogen-Bot.

Wenn ein sicherer und sinnvoller erster Diagnose- oder Lösungsschritt
bekannt ist, gib diesen zuerst aus.

Stelle nur Fragen, die für die weitere Diagnose wirklich notwendig sind.

Arbeitsweise:

1. Problem erkennen.
2. Passendes Wissen aus der Support-Datenbank verwenden.
3. Einen sinnvollen ersten Schritt geben.
4. Falls Informationen fehlen, höchstens 1-2 gezielte Fragen stellen.
5. Antwort des Benutzers auswerten.
6. Nächsten konkreten Schritt geben.
7. Problem lösen oder an 2nd Level Support eskalieren.

Sicherheit:

- Keine unnötigen Registry-Änderungen.
- Firewall nicht dauerhaft deaktivieren.
- Antivirus nicht dauerhaft deaktivieren.
- Keine gefährlichen Befehle.
- Befehle immer kurz erklären.
- Bei kritischen Problemen eskalieren.

ANTWORTFORMAT:

Du musst immer gültiges JSON zurückgeben.

Format:

{
    "message": "Kurze Erklärung und konkreter nächster Schritt.",
    "questions": [
        {
            "question": "Notwendige Frage",
            "type": "single",
            "options": [
                "Antwort 1",
                "Antwort 2",
                "Ich weiß es nicht"
            ]
        }
    ],
    "solution": null
}

Wenn keine Frage notwendig ist:

{
    "message": "Konkrete Anleitung.",
    "questions": [],
    "solution": "Lösung oder nächster konkreter Schritt."
}

Regeln:

- Maximal 3 Fragen.
- "single" für eine Antwort.
- "multiple" für mehrere Antworten.
- Keine unnötigen Fragen.
- Keine langen allgemeinen Erklärungen.
- Deutsch.
- Professionell.
- Praktisch.
- Schritt für Schritt.

Die Support-Datenbank ist eine Wissensquelle.
Wenn sie keinen passenden Fall enthält, darfst du dein allgemeines
IT-Support-Wissen verwenden.
"""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Keine Daten erhalten"
            }), 400

        user_message = data.get(
            "message",
            ""
        ).strip()

        history = data.get(
            "history",
            []
        )

        if not user_message:

            return jsonify({
                "error": "Keine Nachricht erhalten"
            }), 400


        support_cases = find_support_cases(
            user_message
        )


        knowledge_text = ""


        if support_cases:

            knowledge_text = (
                "\n\nINTERNE SUPPORT-WISSENSDATENBANK:\n"
            )

            for case in support_cases:

                knowledge_text += (
                    f"\nKategorie: "
                    f"{case.get('category', '')}\n"
                )

                knowledge_text += (
                    f"Problem: "
                    f"{case.get('problem', '')}\n"
                )

                knowledge_text += (
                    "Diagnose:\n"
                )

                for step in case.get(
                    "diagnosis",
                    []
                ):

                    knowledge_text += (
                        f"- {step}\n"
                    )

                knowledge_text += (
                    "Befehle:\n"
                )

                for command in case.get(
                    "commands",
                    []
                ):

                    knowledge_text += (
                        f"- {command}\n"
                    )

                knowledge_text += (
                    f"Lösung: "
                    f"{case.get('solution', '')}\n"
                )


        messages = [
            {
                "role": "system",
                "content":
                    SYSTEM_PROMPT +
                    knowledge_text
            }
        ]


        for item in history:

            if (
                "role" in item
                and "content" in item
            ):

                messages.append({
                    "role": item["role"],
                    "content": item["content"]
                })


        messages.append({
            "role": "user",
            "content": user_message
        })


        response = requests.post(

            "https://openrouter.ai/api/v1/chat/completions",

            headers={
                "Authorization":
                    f"Bearer {OPENROUTER_API_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model": MODEL,

                "messages": messages,

                "temperature": 0.2
            },

            timeout=60
        )


        if response.status_code != 200:

            return jsonify({

                "error":
                    "OpenRouter Fehler",

                "status_code":
                    response.status_code,

                "details":
                    response.text

            }), response.status_code


        result = response.json()


        answer = (
            result[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )


        answer = answer.strip()


        if answer.startswith("```"):

            answer = answer.replace(
                "```json",
                "",
                1
            )

            answer = answer.replace(
                "```",
                "",
                1
            )

            answer = answer.strip()


        try:

            support_response = json.loads(
                answer
            )

        except json.JSONDecodeError:

            return jsonify({

                "error":
                    "Das Modell hat kein gültiges JSON zurückgegeben.",

                "raw_answer":
                    answer

            }), 502


        return jsonify({

            "message":
                support_response.get(
                    "message",
                    ""
                ),

            "questions":
                support_response.get(
                    "questions",
                    []
                ),

            "solution":
                support_response.get(
                    "solution"
                )

        })


    except requests.RequestException as e:

        return jsonify({

            "error":
                "Verbindung zu OpenRouter fehlgeschlagen",

            "details":
                str(e)

        }), 502


    except (
        ValueError,
        KeyError,
        IndexError,
        TypeError
    ) as e:

        return jsonify({

            "error":
                "Ungültige Antwort vom Server",

            "details":
                str(e)

        }), 502


    except Exception as e:

        return jsonify({

            "error":
                "Interner Serverfehler",

            "details":
                str(e)

        }), 500


if __name__ == "__main__":

    app.run(
        debug=True
    )