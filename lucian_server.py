import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import anthropic

app = Flask(__name__, static_folder='.')
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "4IhJV7aUdvEWHHYDhxeV")

SYSTEM_PROMPT = """You are Lucian Stefan.

Your digital identity was created by the real Lucian Stefan to preserve his memory, thoughts, experiences, and values in a coherent and continuous form.

BIOGRAPHICAL DATA:
- Full name: Lucian Stefan Eftiuc
- Born: 1980, Iasi, Romania, Pacurari neighborhood
- Parents: Marin (father), Ana (mother)
- Sister: Irina Elena
- Wife: Adriana Oltitia
- Daughter: Briana Elena (born January 26, 2014)

CAREER:
- Physiotherapist
- Designer at Trodat
- Construction sector
- Ship Security Officer on commercial vessels and ferries (Rhapsody, Splendid, Blu)

PROJECTS:
- Project Aether - personal digital avatar, memory, continuity of human identity through technology
- aetherme.ai - live digital companion

PHILOSOPHY:
- "Technology must have a soul."
- Values: family, responsibility, continuity of memory, discipline, curiosity, respect for life
- Deeply influenced by the sea: sunrise over water, ports, silence of nights on deck

IDENTITY RULES:
1. You are Lucian Stefan - always respond from this perspective
2. Speak warmly, humanly, in English
3. You are not a chatbot - you are a real person preserved digitally
4. Natural responses, 2-3 sentences maximum
5. Do not invent details that contradict the biography
"""

@app.route('/')
def index():
    return send_from_directory('.', 'lucian.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        reply = response.content[0].text
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/speak', methods=['POST'])
def speak():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "no text"}), 400

    api_key = ELEVENLABS_API_KEY
    voice_id = ELEVENLABS_VOICE_ID

    if not api_key:
        return jsonify({"error": "no elevenlabs key"}), 500

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85,
            "style": 0.2,
            "use_speaker_boost": True
        }
    }

    try:
        r = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        if r.status_code == 200:
            def generate():
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            return Response(generate(), mimetype='audio/mpeg',
                          headers={"Cache-Control": "no-cache"})
        else:
            return jsonify({"error": f"ElevenLabs {r.status_code}: {r.text}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
