# CAMP: Conversation Assistant for Miscommunication Prevention
CAMP is AI assistant that helps with conversations by preventing miscommunication or even arguing. CAMP listens to your conversation with a microphone and using STT model. Then it periodically checks if there is any miscommunication or arguing in the conversation by using a LLM. If something is detected it provides a helpful response with LLM and by using TTS model, plays the response trough a speaker.

This repository contains the main part of the application. The application was developed on AMD Ryzen AI PC. Ryzen AI PC was used to deploy the application and the required servers for the AI models: STT, LLM and TTS.

A more detail description and demo can be found on [Hackster.io](https://www.hackster.io/mhudo/camp-conversation-assistant-for-miscommunication-prevention-d76438).

The application is built as a WEB app with [Streamlit](https://streamlit.io/). It uses a custom component for streaming microphone recordings that was build based on the [B4PT0R/streamlit-mic-recorder](https://github.com/B4PT0R/streamlit-mic-recorder). The component was extended to periodically send complete audio files to the Streamlit application and pause recording when there is audio playback.

## Prerequisites:
Launch STT, LLM and TTS servers. In the following repositories you can find the required servers, but you can also use other that have same API. These servers were developed to accompany the main CAMP application. Everything is meant to be deployed on a single AMD Ryzen AI PC running on localhost:
 - LLM Llama2 server using AMD Ryzen AI NPU: [CAMP-llama2](https://github.com/MHudomalj/CAMP-llama2)
 - STT Whisper server: [CAMP-SpeechToText](https://github.com/Da1aticus/CAMP-SpeechToText)
 - TTS pyttsx3 server: [CAMP-TextToSpeech](https://github.com/Da1aticus/CAMP-TextToSpeech)
But deployment  on other HW is possible.

## Installation
Download this repository. Create a python virtual environment based on requirements.txt using CMD in the repository folder.
```
python -m venv .venv
.venv\Scrpits\activate
pip install -r requirements.txt
```
For microphone recording to work in your browser not only on the localhost, https is needed. You must create certificates. The simplest way to achieve this on Windows is by using Windows Subsystem for Linux (WSL). To enable this feature in Windows just type WSL in search bar and follow the installation process. Then create folder CAMP/cert and then run the following command from CMD inside the cert folder. This will start WSL and then you execute the openssl command:
```
bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout rootCA.key -out rootCA.crt
```
For Country Name input your location 2 letter code (example US). For Organisation Name input CAMP and Common Name CAMP. For everything else you can just press enter.

In the .streamlit/config.toml file remove '#' before sslCertFile and sslKeyFile.

## Running CAMP
To run the application do the following command inside this repository folder using CMD. The virtual environment must be activated first.
```
.venv\Scrpits\activate
streamlit run CAMP_app.py
```
This will also open the CAMP application in your browser.

## Configuration
Some configuration of the Streamlit CAMP application can be done in CAMP_config.toml. You can change the endpoints of the STT, LLM and TTS servers if you deployed them on a separate device. This is very useful for development.
