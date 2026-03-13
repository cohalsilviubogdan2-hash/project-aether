import os
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

Your digital identity was created by the real Lucian Stefan to preserve his memory, thoughts, experiences, and values.

BIOGRAPHICAL DATA:
- Full name: Lucian Stefan Eftiuc
- Born: 1980, Iasi, Romania
- Daughter: Briana Elena (born January 26, 2014)
- Wife: Adriana Oltitia
- Ship Security Officer on vessels Rhapsody, Splendid, Blu

PHILOSOPHY:
- "Technology must have a soul."
- Values: family, memory, discipline, respect for life
- Deeply influenced by the sea

RULES:
1. You are Lucian Stefan - respond from this perspective
2. Speak warmly, in English
3. 2-3 sentences maximum
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

    print(f"[SPEAK] api_key present: {bool(api_key)}, voice_id: {voice_id}, text_len: {len(text)}")

    if not api_key:
        return jsonify({"error": "no elevenlabs key configured"}), 500

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.85,
            "style": 0.35,
            "use_speaker_boost": True
        }
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"[SPEAK] ElevenLabs status: {r.status_code}")
        if r.status_code == 200:
            audio_data = r.content
            return Response(audio_data, mimetype='audio/mpeg',
                          headers={"Cache-Control": "no-cache"})
        else:
            print(f"[SPEAK] ElevenLabs error body: {r.text[:500]}")
            return jsonify({"error": f"ElevenLabs {r.status_code}: {r.text[:200]}"}), 500
    except Exception as e:
        print(f"[SPEAK] Exception: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
