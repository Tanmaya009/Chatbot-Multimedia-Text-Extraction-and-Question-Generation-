import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import speech_recognition as sr
from multiprocessing import Pool, cpu_count
from pytube import YouTube
import fitz  # PyMuPDF
import docx

# Initialize the Generative AI model
try:
    genai.configure(api_key="AIzaSyAlB_2SshxZbk2ghEMMHOj_q5pyyPubWGU")
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"An error occurred while initializing the Gemini API: {e}")

def role_to_streamlit(role):
    if role == "model":
        return "assistant"
    else:
        return role

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

if "uploaded_text" not in st.session_state:
    st.session_state.uploaded_text = ""

st.title("Chat with Tanmaya's Chatbot")
html_temp = """
<div style="background: linear-gradient(to right, #ffcc00, #ff6666, #3399ff, #66ff66); padding: 10px;">
    <h2 style="color: #fff; text-align: center; font-weight: bold; text-shadow: 2px 2px 4px #000000;">Welcome To The Chatbot</h2>
</div>
"""
st.markdown(html_temp, unsafe_allow_html=True)

if "chat" in st.session_state:
    for message in st.session_state.chat.history:
        with st.container():
            st.markdown(message.parts[0].text, unsafe_allow_html=True)

def transcribe_audio_segment(audio_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
    except Exception as e:
        return f"[Error transcribing segment: {e}]"

def extract_audio_segments(video_path, segment_length, overlap):
    video_clip = mp.VideoFileClip(video_path)
    duration = video_clip.duration
    segments = []

    for start in range(0, int(duration), segment_length - overlap):
        end = min(start + segment_length, duration)
        segment = video_clip.subclip(start, end)
        audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
        segment.audio.write_audiofile(audio_path)
        segments.append(audio_path)

    video_clip.close()
    return segments

def process_video(video_path):
    try:
        segment_length = 30  # 30 seconds
        overlap = 5  # 5 seconds overlap

        audio_segments = extract_audio_segments(video_path, segment_length, overlap)

        with Pool(cpu_count()) as pool:
            transcribed_segments = pool.map(transcribe_audio_segment, audio_segments)

        transcribed_text = " ".join(transcribed_segments)
        st.session_state.uploaded_text = transcribed_text

        st.write("Transcribed Text:")
        st.write(transcribed_text)

        prompt = f"Generate 5-5 questions from each Hard, medium, and easy questions from the following text: {transcribed_text}"
        response = st.session_state.chat.send_message(prompt)

        st.write("Generated Questions:")
        st.markdown(response.text)

    except Exception as e:
        st.error(f"An error occurred during transcription: {e}")
    finally:
        for audio_path in audio_segments:
            os.remove(audio_path)

def read_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def read_docx(file_path):
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

uploaded_file = st.file_uploader("Upload a video, PDF, or DOCX file", type=["mp4", "mov", "avi", "pdf", "docx"])

video_url = st.text_input("Or enter a video URL")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1]) as temp_file:
        temp_file.write(uploaded_file.read())
        temp_file_path = temp_file.name

    if uploaded_file.name.endswith(("mp4", "mov", "avi")):
        st.success("Video uploaded successfully!")
        st.video(temp_file_path)
        
        if st.button("Transcribe Uploaded Video to Text"):
            process_video(temp_file_path)
            os.remove(temp_file_path)
    elif uploaded_file.name.endswith("pdf"):
        st.success("PDF uploaded successfully!")
        pdf_text = read_pdf(temp_file_path)
        st.session_state.uploaded_text = pdf_text
        st.write("Extracted Text from PDF:")
        st.write(pdf_text)
        
        if st.button("Generate Questions from PDF Text"):
            prompt = f"Generate 5-5 questions from each Hard, medium, and easy questions from the following text: {pdf_text}"
            response = st.session_state.chat.send_message(prompt)
            
            st.write("Generated Questions:")
            st.markdown(response.text)
    elif uploaded_file.name.endswith("docx"):
        st.success("DOCX uploaded successfully!")
        docx_text = read_docx(temp_file_path)
        st.session_state.uploaded_text = docx_text
        st.write("Extracted Text from DOCX:")
        st.write(docx_text)
        
        if st.button("Generate Questions from DOCX Text"):
            prompt = f"Generate 5-5 questions from each Hard, medium, and easy questions from the following text: {docx_text}"
            response = st.session_state.chat.send_message(prompt)
            
            st.write("Generated Questions:")
            st.markdown(response.text)

if video_url:
    if st.button("Transcribe Video from URL to Text"):
        try:
            yt = YouTube(video_url)
            stream = yt.streams.filter(file_extension='mp4').first()
            temp_video_file_path = stream.download(filename=tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name)
            
            st.success("Video downloaded successfully!")
            st.video(temp_video_file_path)
            
            process_video(temp_video_file_path)
            os.remove(temp_video_file_path)
            
        except Exception as e:
            st.error(f"An error occurred while downloading the video: {e}")

if prompt := st.text_input("I'm help for you"):
    st.container()
    st.markdown(prompt)

    if st.session_state.uploaded_text:
        combined_prompt = f"{st.session_state.uploaded_text} \n\n{prompt}"
    else:
        combined_prompt = prompt

    response = st.session_state.chat.send_message(combined_prompt)

    with st.container():
        st.markdown(response.text)