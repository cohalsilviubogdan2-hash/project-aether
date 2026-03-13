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
DID_API_KEY = os.environ.get("DID_API_KEY", "Y29oYWxzaWx2aXVib2dkYW4yQGdtYWlsLmNvbQ:oIWM78B0oHhB2zP0FGtUh")

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

def get_fresh_image_url():
    """Get a fresh signed S3 URL for Lucian's image from D-ID talks"""
    headers = {"Authorization": f"Basic {DID_API_KEY}"}
    try:
        r = requests.get("https://api.d-id.com/talks?limit=1", headers=headers, timeout=15)
        if r.status_code == 200:
            talks = r.json().get('talks', [])
            if talks:
                return talks[0].get('source_url')
    except Exception as e:
        print(f"[IMAGE] Error getting fresh URL: {e}")
    return None

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

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
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
        if r.status_code == 200:
            return Response(r.content, mimetype='audio/mpeg',
                          headers={"Cache-Control": "no-cache"})
        return jsonify({"error": f"ElevenLabs {r.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/talk', methods=['POST'])
def talk():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "no text"}), 400

    # Step 1: Get audio from ElevenLabs
    el_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    el_headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    el_payload = {
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
        el_r = requests.post(el_url, headers=el_headers, json=el_payload, timeout=30)
        if el_r.status_code != 200:
            return jsonify({"error": f"ElevenLabs {el_r.status_code}"}), 500
        audio_bytes = el_r.content
    except Exception as e:
        return jsonify({"error": f"ElevenLabs: {e}"}), 500

    # Step 2: Upload audio to D-ID
    did_headers = {"Authorization": f"Basic {DID_API_KEY}"}
    try:
        upload_r = requests.post(
            "https://api.d-id.com/audios",
            headers=did_headers,
            files={"audio": ("audio.mp3", audio_bytes, "audio/mpeg")},
            timeout=30
        )
        print(f"[TALK] Audio upload: {upload_r.status_code}")
        if upload_r.status_code not in (200, 201):
            return jsonify({"error": f"D-ID audio {upload_r.status_code}"}), 500
        audio_url = upload_r.json().get("url")
    except Exception as e:
        return jsonify({"error": f"D-ID upload: {e}"}), 500

    # Step 3: Get fresh image URL
    image_url = get_fresh_image_url()
    if not image_url:
        return jsonify({"error": "no image url"}), 500
    print(f"[TALK] Using image URL: {image_url[:80]}...")

    # Step 4: Create D-ID talk
    talk_payload = {
        "source_url": image_url,
        "script": {
            "type": "audio",
            "audio_url": audio_url
        },
        "config": {
            "fluent": True,
            "pad_audio": 0.0,
            "stitch": True
        }
    }
    try:
        talk_r = requests.post(
            "https://api.d-id.com/talks",
            headers={**did_headers, "Content-Type": "application/json"},
            json=talk_payload,
            timeout=30
        )
        print(f"[TALK] Create: {talk_r.status_code} {talk_r.text[:200]}")
        if talk_r.status_code in (200, 201):
            talk_id = talk_r.json().get('id')
            return jsonify({"talk_id": talk_id})
        return jsonify({"error": f"D-ID {talk_r.status_code}: {talk_r.text[:200]}"}), 500
    except Exception as e:
        return jsonify({"error": f"D-ID talk: {e}"}), 500

@app.route('/talk/<talk_id>', methods=['GET'])
def get_talk(talk_id):
    headers = {"Authorization": f"Basic {DID_API_KEY}"}
    try:
        r = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers, timeout=15)
        if r.status_code == 200:
            d = r.json()
            return jsonify({"status": d.get('status'), "result_url": d.get('result_url')})
        return jsonify({"error": f"D-ID {r.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/did-debug', methods=['GET'])
def did_debug():
    headers = {"Authorization": f"Basic {DID_API_KEY}"}
    try:
        r1 = requests.get("https://api.d-id.com/talks?limit=5", headers=headers, timeout=15)
        talks = r1.json() if r1.status_code == 200 else {"error": r1.text[:200]}
        return jsonify({"talks": talks})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
