from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from google.cloud import speech
from google.cloud import texttospeech
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('tts', exist_ok=True)  # Ensure tts folder exists as well


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_files(folder):
    files = []
    for filename in os.listdir(folder):
        if allowed_file(filename):
            files.append(filename)
    files.sort(reverse=True)
    return files


@app.route('/')
def index():
    files = get_files(UPLOAD_FOLDER)  # Files from the 'uploads' folder
    tts_files = get_files('tts')  # Files from the 'tts' folder
    return render_template('index.html', files=files, tts_files=tts_files)


@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)

    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Google Speech-to-Text API integration
        client = speech.SpeechClient()
        with open(file_path, 'rb') as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)

        config = speech.RecognitionConfig(
            # encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            # sample_rate_hertz=24000,
            language_code="en-US",
            model="latest_long",
            audio_channel_count=1,
            enable_word_confidence=True,
            enable_word_time_offsets=True,
        )

        response = client.recognize(config=config, audio=audio)

        # Save transcript to a .txt file
        transcript = "\n".join([result.alternatives[0].transcript for result in response.results])
        transcript_path = file_path + '.txt'
        with open(transcript_path, 'w') as f:
            f.write(transcript)

    return redirect('/')  # success


@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']

    if not text.strip():
        flash("Text input is empty")
        return redirect(request.url)

    # Google Text-to-Speech API integration
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams()
    voice.language_code="en-UK"
    voice.ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)

    # Save the audio to a file in the 'tts' folder
    tts_folder = 'tts'
    filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
    file_path = os.path.join(tts_folder, filename)

    with open(file_path, 'wb') as out:
        out.write(response.audio_content)

    return redirect('/')  # success



# Route to serve files from either uploads or tts folder
@app.route('/<folder>/<filename>')
def uploaded_file(folder, filename):
    if folder not in ['uploads', 'tts']:
        return "Invalid folder", 404

    folder_path = os.path.join(folder, filename)
    if os.path.exists(folder_path):
        return send_from_directory(folder, filename)
    else:
        return "File not found", 404


@app.route('/script.js', methods=['GET'])
def scripts_js():
    return send_from_directory('', 'script.js')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
