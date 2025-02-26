import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from google.cloud import speech
from google.cloud import texttospeech
from google.cloud import language_v2

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
# TTS_FOLDER = 'tts'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['TTS_FOLDER'] = TTS_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(TTS_FOLDER, exist_ok=True)
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


# Google Speech-to-Text API integration
sr_client=speech.SpeechClient()
def sample_recognize(content):
  audio=speech.RecognitionAudio(content=content)

  config=speech.RecognitionConfig(
  # encoding=speech.RecognitionConfig.AudioEncoding.MP3,
  # sample_rate_hertz=24000,
  language_code="en-US",
  model="latest_long",
  audio_channel_count=1,
  enable_word_confidence=True,
  enable_word_time_offsets=True,
  )

  operation=sr_client.long_running_recognize(config=config, audio=audio)

  response=operation.result(timeout=90)

  txt = ''
  for result in response.results:
    txt = txt + result.alternatives[0].transcript + '\n'

  return txt

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

        filename = file_path
        f = open(filename,'rb')
        data = f.read()
        f.close()

        text = sample_recognize(data)

        print(text)

        f = open(filename + '.txt','w')
        f.write("Transcribed input audio is: ")        
        f.write(text)

        sentiment = sample_analyze_sentiment(text)
        #print()
        magnified_score = sentiment.document_sentiment.score * sentiment.document_sentiment.magnitude
        print(f"Sentence magnified sentiment score: {magnified_score}")
        if magnified_score > 0.75:
            print("POSITIVE")
            f.write("Input sentiment is POSITIVE")
        elif magnified_score < -0.75:
            print("NEGATIVE")
            f.write("Input sentiment is NEGATIVE")
        else:
            print("NEUTRAL")
            f.write("Input sentiment is NEUTRAL")
        f.close()


        '''
        print()
        print(sentiment) '''

        # # Google Speech-to-Text API integration
        # client = speech.SpeechClient()
        # with open(file_path, 'rb') as audio_file:
        #     content = audio_file.read()

        # audio = speech.RecognitionAudio(content=content)

        # config = speech.RecognitionConfig(
        #     # encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        #     # sample_rate_hertz=24000,
        #     language_code="en-US",
        #     model="latest_long",
        #     audio_channel_count=1,
        #     enable_word_confidence=True,
        #     enable_word_time_offsets=True,
        # )

        # response = client.recognize(config=config, audio=audio)

        # # Save transcript to a .txt file
        # transcript = "\n".join([result.alternatives[0].transcript for result in response.results])
        # transcript_path = file_path + '.txt'
        # with open(transcript_path, 'w') as f:
        #     f.write(transcript)

    return redirect('/')  # success

# Google Text-to-Speech API integration
tts_client = texttospeech.TextToSpeechClient()
def sample_synthesize_speech(text=None, ssml=None):
    input = texttospeech.SynthesisInput()
    if ssml:
      input.ssml = ssml
    else:
      input.text = text

    voice = texttospeech.VoiceSelectionParams()
    voice.language_code = "en-UK"
    # voice.ssml_gender = "MALE"

    audio_config = texttospeech.AudioConfig()
    audio_config.audio_encoding = "LINEAR16"

    request = texttospeech.SynthesizeSpeechRequest(
        input=input,
        voice=voice,
        audio_config=audio_config,
    )

    response = tts_client.synthesize_speech(request=request)

    return response.audio_content

@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    print(text)
    
    wav = sample_synthesize_speech(text)
    
    # Save the audio to a file in the 'tts' folder
    filename = 'tts' + datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    f = open(file_path,'wb')
    f.write(wav)
    f.close()

    #save text
    f = open(file_path + '.txt','w')
    f.write("Input text is: ")
    f.write(text)

    sentiment = sample_analyze_sentiment(text)
    #print()
    magnified_score = sentiment.document_sentiment.score * sentiment.document_sentiment.magnitude
    print(f"Sentence magnified sentiment score: {magnified_score}")
    if magnified_score > 0.75:
        print("POSITIVE")
        f.write("\nInput sentiment is POSITIVE")
    elif magnified_score < -0.75:
        print("NEGATIVE")
        f.write("\nInput sentiment is NEGATIVE")
    else:
        print("NEUTRAL")
        f.write("\nInput sentiment is NEUTRAL")
    f.close()

    # print()
    # print(sentiment)

    # if not text.strip():
    #     flash("Text input is empty")
    #     return redirect(request.url)




    # Google Text-to-Speech API integration
    # client = texttospeech.TextToSpeechClient()

    # input_text = texttospeech.SynthesisInput(text=text)
    # voice = texttospeech.VoiceSelectionParams()
    # voice.language_code="en-UK"
    # voice.ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    # audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    # response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)

    # # Save the audio to a file in the 'tts' folder
    # tts_folder = 'tts'
    # filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
    # file_path = os.path.join(tts_folder, filename)

    # with open(file_path, 'wb') as out:
    #     out.write(response.audio_content)

    return redirect('/')  # success

# Google Sentiment Analysis API integration
def sample_analyze_sentiment(text_content: str):
    """
    Analyzes Sentiment in a string.

    Args:
      text_content: The text content to analyze.
    """

    sa_client = language_v2.LanguageServiceClient()

    # text_content = 'I am so happy and joyful.'

    # Available types: PLAIN_TEXT, HTML
    document_type_in_plain_text = language_v2.Document.Type.PLAIN_TEXT

    # Optional. If not specified, the language is automatically detected.
    # For list of supported languages:
    # https://cloud.google.com/natural-language/docs/languages
    language_code = "en"
    document = {
        "content": text_content,
        "type_": document_type_in_plain_text,
        "language_code": language_code,
    }

    # Available values: NONE, UTF8, UTF16, UTF32
    # See https://cloud.google.com/natural-language/docs/reference/rest/v2/EncodingType.
    encoding_type = language_v2.EncodingType.UTF8

    response = sa_client.analyze_sentiment(
        request={"document": document, "encoding_type": encoding_type}
    )
    # Get overall sentiment of the input document
    print(f"Document sentiment score: {response.document_sentiment.score}")
    print(f"Document sentiment magnitude: {response.document_sentiment.magnitude}")
    # Get sentiment for all sentences in the document
    for sentence in response.sentences:
        print(f"Sentence text: {sentence.text.content}")
        print(f"Sentence sentiment score: {sentence.sentiment.score}")
        print(f"Sentence sentiment magnitude: {sentence.sentiment.magnitude}")

    # Get the language of the text, which will be the same as
    # the language specified in the request or, if not specified,
    # the automatically-detected language.
    print(f"Language of the text: {response.language_code}")

    return response

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
    app.run(debug=True, port=8080)
