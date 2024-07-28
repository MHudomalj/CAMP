import os
import streamlit as st
import streamlit.components.v1 as components
import base64

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component("streamlit_mic_recorder", url="http://localhost:3001")
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component("streamlit_mic_recorder", path=build_dir)


def mic_recorder(
        start_prompt="Start recording",
        stop_prompt="Stop recording",
        use_container_width=False,
        format="webm",
        audio_chunk_time=1000,
        audio_chunks_number=8,
        audio_min_start_time=5000,
        audio_callback=None,
        button_callback=None,
        player_callback=None,
        audio_args=(),
        key=None
):
    if '_last_mic_recorder_audio_id' not in st.session_state:
        st.session_state._last_mic_recorder_audio_id = 0
    if (key is not None) and (key+'_output' not in st.session_state):
        st.session_state[key+'_output'] = None
    new_output = False
    component_value = _component_func(
        start_prompt=start_prompt,
        stop_prompt=stop_prompt,
        use_container_width=use_container_width,
        format=format,
        audio_chunk_time=audio_chunk_time,
        audio_chunks_number=audio_chunks_number,
        audio_min_start_time=audio_min_start_time,
        key=key,
        default=None)
    output = None
    if component_value is not None:
        new_output = (component_value["id"] > st.session_state._last_mic_recorder_audio_id)
        st.session_state._last_mic_recorder_audio_id = component_value["id"]
    if new_output:
        if component_value['type'] == "button":
            output = None
            if button_callback is not None:
                button_callback(component_value["value"])
        elif component_value['type'] == "player":
            output = None
            if player_callback is not None:
                player_callback(component_value["value"])
        elif component_value['type'] == "audio":
            audio_bytes = base64.b64decode(component_value["audio_base64"])
            sample_rate = component_value["sample_rate"]
            sample_width = component_value["sample_width"]
            format = component_value["format"]
            id_val = component_value["id"]
            cycle = component_value["cycle"]
            output = {"bytes": audio_bytes,
                      "sample_rate": sample_rate,
                      "sample_width": sample_width,
                      "format": format,
                      "id": id_val,
                      "cycle": cycle
                      }
            if key:
                st.session_state[key+'_output'] = output
            if audio_callback is not None:
                audio_callback(*audio_args)
    return output
