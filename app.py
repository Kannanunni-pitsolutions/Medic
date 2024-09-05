import pyaudio
import speech_recognition as sr
from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import openai
from llm import cds_helper_ddx 
import os
from concurrent.futures import ThreadPoolExecutor

openai.api_key=os.getenv('OPENAI_API_KEY')

app = Flask(__name__)
CORS(app)  # Add this line to enable CORS
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow connections from any origin

# Initialize state store
state_store = {
    "transcript": "",
    "stop_listening": None
}

recognizer = sr.Recognizer()
microphone = sr.Microphone()

def process_audio(recognizer, audio, model, fn):
    try:
        #text = recognizer.recognize_whisper_api(audio, api_key=openai.api_key)
        text = recognizer.recognize_google(audio)
        print("[whisper] transcript: ", text)

        if len(text) > 8:
            fn(text)
        else:
            print("[whisper] ignored because noise:", text)
    except sr.UnknownValueError:
        print("[whisper] Whisper could not understand audio")
    except sr.RequestError as e:
        print(f"[whisper] Could not request results from Whisper service; {e}")

voice_recognition_executor = ThreadPoolExecutor(4)

def get_callback(fn):
    def callback(recognizer, audio):
        voice_recognition_executor.submit(process_audio, recognizer, audio, "small.en", fn)
    return callback

@socketio.on('start_transcription')
def start_transcription():
    with microphone as source:
        print("[whisper] Calibrating...")
        recognizer.adjust_for_ambient_noise(source)

    def example_callback(text):
        print("Transcribed text:", text)
        state_store["transcript"] += " " + text
        #memory.chat_memory.add_user_message(text)
        socketio.emit('transcription', {'text': text})

        # Process transcription to get differential diagnosis
        if len(state_store["transcript"]) > 20:  # Ensure some transcription length
            try:
                # Create an input dictionary for the RunnableSequence
                input_data = {"transcript": state_store["transcript"]}
                
                # Run the RunnableSequence and get the result
                diagnosis_result = cds_helper_ddx.invoke(input_data)
                print("Differential Diagnosis:", diagnosis_result)
                
                # Emit the differential diagnosis result
                socketio.emit('differential_diagnosis', {'diagnosis': diagnosis_result})
            except Exception as e:
                print(f"Error processing differential diagnosis: {e}")
                socketio.emit('differential_diagnosis', {'diagnosis': 'Error processing diagnosis'})

    callback = get_callback(example_callback)
    print("[whisper] Listening...")
    state_store["stop_listening"] = recognizer.listen_in_background(microphone, callback, phrase_time_limit=10)
    emit('transcription_started')

@socketio.on('stop_transcription')
def stop_transcription():
    if state_store["stop_listening"]:
        state_store["stop_listening"]()
        emit('transcription_stopped')
        print("[whisper] Transcription stopped")
    else:
        print("[whisper] No transcription is currently running")

@socketio.on('connect')
def handle_connect():
    print("Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False, port=5000)
    #app.run(debug=True, port=8080, host='0.0.0.0')