import json
import os
import signal
import time

import requests
import speech_recognition as sr
from loguru import logger

try:
    import snowboydecoder
except Exception as exc:
    try:
        from . import snowboydecoder
    except Exception as inner_exc:
        snowboydecoder = None
        _snowboy_error = inner_exc
    else:
        _snowboy_error = None
else:
    _snowboy_error = None


interrupted = False
def _native_safe_snowboy_path(*parts):
    # Snowboy native library fails when the absolute project path contains spaces.
    relative = os.path.join("snowboy", *parts)
    if os.path.exists(relative):
        return relative
    return os.path.join(os.path.dirname(__file__), *parts)


model = _native_safe_snowboy_path("assistxiaoxiao.pmdl")
_wake_words = ("\u5c0f\u5c0f", "\u6653\u6653", "\u5c0f\u6653", "\u52a9\u624b", "\u8bed\u97f3\u52a9\u624b")


def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    return interrupted


def callback():
    print("hi")


signal.signal(signal.SIGINT, signal_handler)

detector = None
_force_speech_fallback = os.environ.get("SNOWBOY_FORCE_SPEECH_FALLBACK", "true").lower() not in ("0", "false", "no")
if snowboydecoder is not None and not _force_speech_fallback:
    try:
        detector = snowboydecoder.HotwordDetector(model, sensitivity=0.4, audio_gain=3)
        logger.info("Snowboy service is loaded")
    except Exception as exc:
        _snowboy_error = exc
        detector = None

if detector is None:
    if _force_speech_fallback:
        logger.info("Snowboy speech fallback is enabled")
    else:
        logger.warning(f"Snowboy native detector unavailable, use speech fallback: {_snowboy_error}")


def _recognize_audio(audio):
    from const_config import azure_key

    if not azure_key:
        return ""
    wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
    url = "https://eastasia.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=zh-CN"
    headers = {
        "Accept": "application/json;text/xml",
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Ocp-Apim-Subscription-Key": azure_key,
    }
    try:
        response = requests.post(url, headers=headers, data=wav_data, timeout=8)
        return json.loads(response.text).get("DisplayText", "")
    except Exception as exc:
        logger.warning(f"fallback hotword recognition failed: {exc}")
        return ""


def _speech_fallback_start(callback):
    recognizer = sr.Recognizer()
    with sr.Microphone(sample_rate=16000) as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        logger.info("Speech fallback hotword listener started")
        while not interrupt_callback():
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
            except sr.WaitTimeoutError:
                continue
            except Exception as exc:
                logger.warning(f"fallback hotword microphone error: {exc}")
                time.sleep(1)
                continue

            text = _recognize_audio(audio)
            if text:
                logger.info(f"Fallback hotword recognize result: {text}")
            normalized = "".join(ch for ch in text if not ch.isspace())
            if any(word in normalized for word in _wake_words):
                logger.info("Fallback hotword detected")
                callback()
                time.sleep(2)


def start(callback):
    if detector is not None:
        detector.start(
            detected_callback=callback,
            interrupt_check=interrupt_callback,
            sleep_time=0.02,
        )
        return
    _speech_fallback_start(callback)


def terminate():
    global interrupted
    interrupted = True
    if detector is not None:
        detector.terminate()
