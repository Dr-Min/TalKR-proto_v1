import streamlit as st
from openai import OpenAI
import pyaudio
import wave 
import os
from pydub import AudioSegment
from pydub.playback import play
import time

assistant_id = st.secrets["assistant_id"]
thread_id = st.secrets["thread_id"]

# Streamlit 앱 설정
st.title("음성 대화 AI 비서")

# 사이드바 설정
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password", value="sk-proj-ceyCqKqrC5woLyNIny2RT3BlbkFJa9YfiRIn9v2JrtoTKfh")
    client = OpenAI(api_key=openai_api_key)
    
    thread_id = st.text_input("Thread ID", value=thread_id)
    
    if st.button("새 대화 시작"):
        thread = client.beta.threads.create()
        thread_id = thread.id
        st.success(f"새 대화가 시작되었습니다. Thread ID: {thread_id}")

# 음성 녹음 함수
def record_audio(filename, duration=5):
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100

    p = pyaudio.PyAudio()
    stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

    st.write("녹음 중...")
    frames = [stream.read(chunk) for _ in range(0, int(rate / chunk * duration))]
    st.write("녹음 완료.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

# 음성을 텍스트로 변환
def speech_to_text(filename):
    with open(filename, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="ko")
    return transcript.text

# OpenAI API를 사용하여 응답 생성
def generate_response(thread_id, user_input):
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)

    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    assistant_message = messages.data[0].content[0].text.value
    return assistant_message

# OpenAI TTS를 사용하여 텍스트를 음성으로 변환
def text_to_speech(text, filename="response.mp3"):
    response = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=text
    )
    response.stream_to_file(filename)

# 음성 파일 재생
def play_audio(filename):
    sound = AudioSegment.from_mp3(filename)
    play(sound)

# 메인 앱 로직
if thread_id:
    if st.button("대화 시작"):
        audio_file = "recorded_audio.wav"
        record_audio(audio_file)
        
        user_text = speech_to_text(audio_file)
        st.write(f"사용자: {user_text}")
        
        assistant_response = generate_response(thread_id, user_text)
        st.write(f"AI 비서: {assistant_response}")
        
        response_audio = "response.mp3"
        text_to_speech(assistant_response, response_audio)
        play_audio(response_audio)
        
        st.success("대화가 성공적으로 처리되었습니다.")
else:
    st.warning("먼저 사이드바에서 새 대화를 시작하세요.")

# 대화 히스토리 표시
if thread_id:
    st.subheader("대화 히스토리")
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        role = "사용자" if msg.role == "user" else "AI 비서"
        st.text(f"{role}: {msg.content[0].text.value}")
