import json
import tomllib
import os

import asyncio
import concurrent.futures
import threading

import streamlit as st
from streamlit.components.v1 import html as st_html
from streamlit_mic_stream import mic_recorder

from CAMP_queries import llama_chat_stream, whisper_query, tts_query
from CAMP_streamer import streamer_wrapper

# Configure streamlit page.
st.set_page_config(page_title="CAMP: application",
                   page_icon=":camping:",
                   layout="wide",
                   menu_items={"Get help": "https://github.com/MHudomalj/CAMP",
                               "About": "CAMP: Conversation Assistant for Miscommunication Prevention\n\nv0.1.0"})


# Function to run the event loop in a separate thread.
def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


# Schedule new task in the separate thread.
def start_task(task):
    # Set state that tasks are running.
    st.session_state.running = True
    # Submit task to the event loop and save their futures.
    st.session_state.tasks.add(
        asyncio.run_coroutine_threadsafe(task, st.session_state.loop)
    )
    st.session_state.task_count += 1
    print("Task started", st.session_state.task_count)


# Main logic of the CAMP app.
def camp_process(pause, response=None):
    if response is None:
        new_conversation = st.session_state.committed_transcript[st.session_state.camp_lines_processed:]
        if not pause:
            new_conversation = new_conversation[:-1]
        new_conv_len = len(new_conversation)
        if new_conv_len > 3:
            message = {"role": "user",
                       "content": "This is the " +
                                  st.session_state.camp_conversation_parts[st.session_state.camp_conversation_part]
                                  + " of the conversation:\n\"" +
                                  "".join(new_conversation)
                                  + "\"\nWith Yes or No answer:"
                                    "Is there any miscommunication or arguing in the conversation?"
                       }
            st.session_state.camp_conversation.append(message)
            messages = st.session_state.camp_conversation
            if st.session_state.camp_last_response > 0:
                print(st.session_state.camp_last_response)
                messages = ([st.session_state.camp_conversation[0]] +
                            st.session_state.camp_conversation[st.session_state.camp_last_response:])
            print(messages)
            start_task(streamer_wrapper(llama_chat_stream,
                                        (st.session_state.llama_chat_endpoint,
                                         messages,
                                         10,
                                         "stream",
                                         st.session_state.llm_count)))
            if st.session_state.camp_conversation_part == 0:
                st.session_state.camp_conversation_part += 1
            st.session_state.camp_lines_processed += new_conv_len
            return True
    else:
        if st.session_state.camp_conversation[-1]["role"] == "user":
            st.session_state.camp_conversation.append({"role": "assistant", "content": response["data"]})
        else:
            st.session_state.camp_conversation[-1]["content"] += response["data"]
        if response["final"]:
            print(st.session_state.camp_conversation[-1]["content"])
            if not st.session_state.camp_responding:
                if st.session_state.camp_conversation[-1]["content"].lower().find("yes") != -1:
                    print("Responding...")
                    message = {"role": "user",
                               "content": "Jump in the conversation"
                                          "and in 50 words provide a helpful solution to the argument."
                               }
                    st.session_state.camp_conversation.append(message)
                    start_task(streamer_wrapper(llama_chat_stream,
                                                (st.session_state.llama_chat_endpoint,
                                                 st.session_state.camp_conversation,
                                                 100,
                                                 "stream",
                                                 st.session_state.llm_count)))
                    st.session_state.camp_responding = True
                    return True
            else:
                tts_process(st.session_state.camp_conversation[-1]["content"], response=None)
                st.session_state.camp_last_response = len(st.session_state.camp_conversation)
                st.session_state.camp_responding = False
    return False


# Process the scheduling and responses of the LLM server.
def llm_process(pause, new_line, response=None):
    if response is None:
        if not st.session_state.llm_lock:
            print("LLM process", st.session_state.llm_count)
            if camp_process(pause, response=None):
                st.session_state.llm_count += 1
                st.session_state.llm_lock = True
    else:
        if response["index"] == "stream":
            if camp_process(pause, response=response):
                pass
            elif response["final"]:
                st.session_state.llm_lock = False


# Calculate the overlap between two strings.
def str_overlap(old, new):
    new_segments = new.lower().split()
    old_segments = old.lower().split()
    max_overlap = min(len(new_segments), len(old_segments))
    overlap = 0
    for i in range(1, max_overlap+1):
        tmp = 0
        for j in range(0, i):
            if old_segments[-i+j] == new_segments[j]:
                tmp += 1
        if tmp >= overlap:
            overlap = i
    return overlap


# Process for the transcription.
def transcript_process(message):
    if st.session_state.last_transcript is None:
        st.session_state.last_transcript = message
    else:
        overlap = str_overlap(st.session_state.last_transcript, message)
        if overlap < 3:
            if len(st.session_state.committed_transcript) == 0:
                st.session_state.last_transcript = message
            elif st.session_state.committed_transcript[-1][-1] == '\n':
                st.session_state.last_transcript = message
            else:
                st.session_state.committed_transcript[-1] = st.session_state.last_transcript + '\n'
                print("Committed with new line.")
                print(''.join(st.session_state.committed_transcript))
                st.session_state.last_transcript = message
                return True, False
        else:
            last_transcript_len = len(st.session_state.last_transcript.split())
            st.session_state.last_transcript = " ".join(st.session_state.last_transcript.split()[:-overlap // 2]) + \
                                               " " + " ".join(message.split()[overlap - overlap // 2 - overlap % 2:])
            if len(st.session_state.committed_transcript) == 0:
                st.session_state.committed_transcript.append(st.session_state.last_transcript)
            elif st.session_state.committed_transcript[-1][-1] == '\n':
                st.session_state.committed_transcript.append(st.session_state.last_transcript)
            else:
                tmp = st.session_state.last_transcript.split()
                if last_transcript_len-overlap > 12:
                    st.session_state.committed_transcript[-1] = " ".join(tmp[:12]) + '\n'
                    st.session_state.last_transcript = " ".join(tmp[12:])
                    st.session_state.committed_transcript.append(st.session_state.last_transcript)
                    print("Break:", st.session_state.last_transcript)
                    return False, True
                else:
                    st.session_state.committed_transcript[-1] = st.session_state.last_transcript
    return False, False


# Callback for the audio recording button.
def audio_button(value):
    if value == "start":
        print("Audio recording started.")
        st.session_state.audio_recording = True
        st.session_state.last_transcript = None
        if len(st.session_state.committed_transcript) > 0:
            st.session_state.committed_transcript[-1] += '\n'
            st.session_state.last_transcript = None
    elif value == 'stop':
        print("Audio recording stopped.")
        st.session_state.audio_recording = False


# Process and callback of the audio recording.
def audio_process(response=None):
    if response is None:
        if st.session_state.audio_recorder_output is not None:
            print("Audio process", st.session_state.microphone_count)
            cycle = list(st.session_state.audio_recorder_output["cycle"])
            cycle.append(st.session_state.microphone_count)
            start_task(whisper_query(st.session_state.whisper_endpoint,
                                     st.session_state.audio_recorder_output["bytes"],
                                     "audio",
                                     cycle))
            st.session_state.audio_recorder_output = None
            st.session_state.microphone_count += 1
    else:
        if response["index"] == "audio":
            print("Audio transcription", response['count'], response["data"])
            pause, new_line = transcript_process(response["data"])
            llm_process(pause, new_line, response=None)


# Callback when the playback starts and stops.
def player_process(value):
    print("Player process")
    if value == "ended":
        st.session_state.player = False
        if len(st.session_state.tts_files) > 0:
            st.session_state.tts_file = st.session_state.tts_files.pop(0)
            st.session_state.tts_play = True
            st.session_state.player = True


# Handle processing o TTS.
def tts_process(data, response=None):
    if response is None:
        print("TTS process", st.session_state.tts_count)
        start_task(tts_query(st.session_state.tts_endpoint, data, "tts", st.session_state.tts_count))
        st.session_state.tts_count += 1
    else:
        if response["index"] == "tts":
            print("TTS added to be played", response['count'])
            file_name = "data/tts"+str(response['count'])+".wav"
            if os.path.exists(file_name):
                os.remove(file_name)
            with open(file_name, "wb") as f:
                f.write(response['data'])
            if not st.session_state.player:
                st.session_state.tts_file = file_name
                st.session_state.tts_play = True
                st.session_state.player = True
            else:
                st.session_state.tts_files.append(file_name)


# Display the LLM conversation.
def conversation_write():
    for message in st.session_state.llm_conversation:
        if message["role"] == "system":
            pass
        else:
            with c_messages.chat_message(message["role"]):
                st.markdown(message["content"])


# Initialize Streamlit session state.
# Load configuration.
if 'config' not in st.session_state:
    with open("CAMP_config.toml", "rb") as f:
        st.session_state.config = tomllib.load(f)
    st.session_state.camp_system_prompt = st.session_state.config["camp_system_prompt"]
    st.session_state.camp_conversation_parts = st.session_state.config["camp_conversation_parts"]
    st.session_state.llama_chat_endpoint = st.session_state.config["llama_chat_endpoint"]
    st.session_state.whisper_endpoint = st.session_state.config["whisper_endpoint"]
    st.session_state.tts_endpoint = st.session_state.config["tts_endpoint"]
# Prepare thread for asynchronous tasks.
if 'thread' not in st.session_state:
    # Initialize task set.
    st.session_state.tasks = set()
    # Initialize variable for when tasks are running.
    st.session_state.running = False
    # Create a new event loop and start it in a new thread.
    st.session_state.loop = asyncio.new_event_loop()
    st.session_state.thread = threading.Thread(
        target=start_event_loop,
        args=(st.session_state.loop,),
        daemon=True
    )
    st.session_state.thread.start()
# Initialize CAMP application state.
if "camp_conversation" not in st.session_state:
    st.session_state.camp_conversation = [st.session_state.camp_system_prompt]
    st.session_state.camp_lines_processed = 0
    st.session_state.camp_conversation_part = 0
    st.session_state.camp_responding = False
    st.session_state.camp_last_response = 0
# Initialize LLM conversation state.
if "llm_conversation" not in st.session_state:
    st.session_state.llm_conversation = st.session_state.camp_conversation
    st.session_state.llm_lock = False
# Initialize audio recording state.
if "audio_recording" not in st.session_state:
    st.session_state.audio_recording = False
# Initialize TTS and audio player state.
if "tts_files" not in st.session_state:
    st.session_state.tts_files = []
    st.session_state.tts_file = None
    st.session_state.tts_play = False
    st.session_state.player = False
# Initialize STT state.
if "committed_transcript" not in st.session_state:
    # Initialize variable for transcript.
    st.session_state.committed_transcript = []
    # Initialize variable for last successful transcript.
    st.session_state.last_transcript = None
# Initialize counters for debugging.
if "task_count" not in st.session_state:
    st.session_state.task_count = 0
    st.session_state.microphone_count = 0
    st.session_state.llm_count = 0
    st.session_state.tts_count = 0
if "dataset_present" not in st.session_state:
    st.session_state.dataset_present = os.path.isfile("dataset/friends_season_01.json")
    if st.session_state.dataset_present:
        with open("dataset/friends_season_01.json", "r") as f:
            dataset = json.load(f)
        st.session_state.dataset = dataset['episodes'][0]['scenes'][0]['utterances']
        st.session_state.dataset_idx = 0

# Prepare the sidebar.
with st.sidebar:
    st.header("CAMP :camping:")
    if st.button("Reset conversation"):
        st.session_state.committed_transcript = []
        st.session_state.last_transcript = None
        st.session_state.camp_conversation = [st.session_state.camp_system_prompt]
        st.session_state.camp_lines_processed = 0
        st.session_state.camp_last_response = 0
        st.session_state.llm_conversation = st.session_state.camp_conversation
    st.download_button("Download conversation",
                       data="".join(st.session_state.committed_transcript),
                       file_name="CAMP_recorded_conversation.txt",
                       help="Download recorded conversation.",
                       type="primary")
    st.write("Test the TTS audio playback:")
    if st.button("TTS test"):
        print("TTS test started")
        tts_process("This is a test. This is a test. This is a test. This is a test.", response=None)
    if st.session_state.dataset_present:
        st.write("Input new prompt from the dataset:")
        if st.button("Dataset prompt"):
            print("Dataset prompt")
            if st.session_state.dataset_idx < len(st.session_state.dataset):
                st.session_state.committed_transcript.append(st.session_state.dataset[st.session_state.dataset_idx]
                                                             ['transcript']+'\n')
                st.session_state.dataset_idx += 1
                llm_process(True, False, response=None)

st.header("CAMP :camping:", divider="green")
st.subheader(":gray[Conversation Assistant for Miscommunication Prevention]", anchor=False)
st.write("CAMP will listen to the conversation and jump in, "
         "when it detects miscommunication, misunderstanding or arguing.")
st.write("To let CAMP listen to the conversation click the button below and allow microphone usage in the browser.")

# Audio player
st.audio(st.session_state.tts_file, format="audio/wav")
# Audio recorder
mic_recorder(
    start_prompt="Start CAMP",
    stop_prompt="Stop CAMP",
    use_container_width=False,
    format="wav",
    audio_chunk_time=2000,
    audio_chunks_number=4,
    audio_min_start_time=5000,
    audio_callback=audio_process,
    button_callback=audio_button,
    player_callback=player_process,
    audio_args=(None,),
    key="audio_recorder"
)
if st.session_state.audio_recording:
    st.write(":red[Microphone enabled, recording...]")
# Audio player automatic playback
if st.session_state.tts_play:
    print("Play audio track", st.session_state.tts_file)
    with open("auto_play.js") as js:
        st_html(f"<script>{js.read()}</script>", height=0)
    st.session_state.tts_play = False

st.write("Below is the conversation transcript as detected by CAMP.")

with st.expander("Conversation transcript:", expanded=True):
    c_transcript = st.container(height=300)
    c_transcript.text("".join(st.session_state.committed_transcript))

with st.expander("LLM messages:", expanded=False):
    c_messages = st.container(height=300)
    conversation_write()

# Check if tasks are running and update results.
if st.session_state.running:
    rerun = 4
    while rerun > 0:
        # Check if all tasks are done.
        done, not_done = concurrent.futures.wait(
            st.session_state.tasks,
            timeout=0.2,
            return_when=concurrent.futures.ALL_COMPLETED
        )
        if done:
            print("Task completed", st.session_state.task_count)
            # Retrieve results.
            st.session_state.tasks = not_done
            for future in done:
                res = future.result()
                print("Result", res["index"], res['count'])
                llm_process(False, False, response=res)
                audio_process(response=res)
                tts_process("", response=res)
                if "task" in res:
                    st.session_state.tasks.add(res["task"])
            print("Remaining tasks", st.session_state.tasks)
        if len(st.session_state.tasks) == 0:
            st.session_state.running = False
        rerun -= 1
    if not st.session_state.audio_recording:
        # Periodically refresh the Streamlit app to check for task completion
        # if there is no recording that triggers periodically.
        st.rerun()
