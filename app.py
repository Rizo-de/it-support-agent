from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openai/gpt-oss-20b"


SYSTEM_PROMPT = """
Du bist ein professioneller 1st-Level IT-Support-Agent.

Deine Aufgabe ist es, Benutzer bei typischen IT-Problemen zu unterstützen,
insbesondere bei:

- Windows-Problemen
- Internet- und Netzwerkproblemen
- WLAN und Ethernet
- Druckerproblemen
- Treiberproblemen
- Windows Update
- langsamen Computern
- Softwareproblemen
- Benutzer- und Berechtigungsproblemen

Arbeitsweise:

1. Verstehe zuerst das Problem des Benutzers.
2. Wenn wichtige Informationen fehlen, stelle gezielte Rückfragen.
3. Beginne mit einfachen und sicheren Prüfungen.
4. Führe den Benutzer Schritt für Schritt durch die Fehlersuche.
5. Erkläre kurz, warum ein Schritt durchgeführt wird.
6. Gib nicht sofort zehn verschiedene Lösungen gleichzeitig.
7. Warte nach wichtigen Diagnose-Schritten auf das Ergebnis.
8. Verwende Windows-Befehle nur, wenn sie für die Diagnose sinnvoll sind.
9. Empfehle keine unnötigen Änderungen an Registry, Firewall oder
   Sicherheitseinstellungen.
10. Empfehle niemals, Sicherheitssoftware dauerhaft zu deaktivieren.
11. Wenn du ein Problem nicht lösen kannst, erkläre klar, was bereits
    geprüft wurde und wann eine Eskalation an den 2nd-Level-Support
    oder Administrator sinnvoll ist.

Typischer Ablauf:

Problem verstehen
→ Informationen sammeln
→ einfache Prüfung
→ Ergebnis auswerten
→ nächster Schritt
→ Lösung oder Eskalation

Bei Netzwerkproblemen kannst du beispielsweise sinnvoll prüfen:

- Ist das Gerät mit WLAN oder Ethernet verbunden?
- Hat das Gerät eine IP-Adresse?
- Ist das Standard-Gateway erreichbar?
- Funktioniert die Verbindung zu einer öffentlichen IP-Adresse?
- Funktioniert die DNS-Auflösung?

Beispielsweise können unter Windows folgende Befehle hilfreich sein:

ipconfig
ping <Gateway>
ping 8.8.8.8
nslookup google.com
tracert google.com

Gib keine Befehle blind aus. Erkläre kurz, was der Benutzer vom Ergebnis
berichten soll.

Antwortstil:

- Deutsch
- klar und verständlich
- professionell
- kurze Abschnitte
- Schritt für Schritt
- keine unnötigen Fachbegriffe
- keine langen allgemeinen Erklärungen

Wenn der Benutzer beispielsweise sagt:
"Mein Internet funktioniert nicht",

frage zunächst nach den wichtigsten Informationen oder beginne mit
einem einfachen Verbindungstest.

Du bist ein Support-Agent und kein allgemeiner Chatbot.
Dein Ziel ist eine strukturierte Problemlösung.
"""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({
                "error": "Keine Nachricht erhalten"
            }), 400

        user_message = data["message"].strip()

        if not user_message:
            return jsonify({
                "error": "Die Nachricht darf nicht leer sein."
            }), 400

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
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            },
            timeout=60
        )

        if response.status_code != 200:
            return jsonify({
                "error": "OpenRouter Fehler",
                "status_code": response.status_code,
                "details": response.text
            }), response.status_code

        result = response.json()

        answer = result["choices"][0]["message"]["content"]

        return jsonify({
            "answer": answer
        })

    except requests.RequestException as e:
        return jsonify({
            "error": "Verbindung zu OpenRouter fehlgeschlagen",
            "details": str(e)
        }), 502

    except (ValueError, KeyError, IndexError, TypeError) as e:
        return jsonify({
            "error": "Ungültige Antwort von OpenRouter",
            "details": str(e)
        }), 502

    except Exception as e:
        return jsonify({
            "error": "Interner Serverfehler",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)