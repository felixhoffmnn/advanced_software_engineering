from pathlib import Path

import speech_recognition as sr
from pyttsx3 import Engine

from aswe.core.user_interaction import SpeechToText, TextToSpeech


def test_convert_file() -> None:
    """Test if the speech is parsed correctly"""
    audio_path = Path("data/test_user_interaction.wav")
    stt = SpeechToText(get_mic=False)
    assert isinstance(stt, SpeechToText)
    assert isinstance(stt.recognizer, sr.Recognizer)

    parsed_text = stt.convert_audio_file(audio_path)
    assert isinstance(parsed_text, str)
    assert parsed_text in (
        "this is a test for the text to speech conversion",
        "this is a test for the text-to-speech conversion",
    )


def test_convert_text() -> None:
    """Test if text is parsed without any errors."""
    tts = TextToSpeech()
    assert isinstance(tts, TextToSpeech)
    assert isinstance(tts.engine, Engine)

    tts.convert_text("This is a test for the text to speech conversion.")


def test_optimize_time_for_speech() -> None:
    """Test if the time is optimized for speech correctly."""
    tts = TextToSpeech()

    text_with_time_1 = "The event is at 12:00"
    text_with_time_2 = "The event is at 13:45"

    assert tts.optimize_time_for_speech(text_with_time_1) == "The event is at 12 o'clock"
    assert tts.optimize_time_for_speech(text_with_time_2) == "The event is at 13 45"
