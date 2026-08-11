"""Diagnostic tool to test and benchmark the quality of 'sherlock.onnx' wake-word model in real-time.

Prints live audio volume levels and prediction scores for 'sherlock.onnx' alongside
openWakeWord reference built-in models ('hey_jarvis', 'alexa') for direct quality comparison.
"""

import sys
import time
import sounddevice as sd
import numpy as np
import openwakeword
from openwakeword.model import Model

def extract_score(prediction, key: str) -> float:
    """Safely extracts prediction score from dict, tuple, or list openWakeWord outputs."""
    if isinstance(prediction, dict):
        return float(prediction.get(key, 0.0))
    elif isinstance(prediction, (tuple, list)) and len(prediction) > 0:
        item = prediction[0]
        if isinstance(item, dict):
            return float(item.get(key, 0.0))
    return 0.0


def main():
    print("=" * 65)
    print("      Sherlock ONNX Wake-Word Real-Time Quality Tester")
    print("=" * 65)

    model_path = "models/sherlock.onnx"
    models_to_load = [model_path, "hey_jarvis", "alexa"]

    print(f"Loading target custom model: {model_path}")
    try:
        oww_model = Model(wakeword_models=models_to_load, inference_framework="onnx")
        loaded_keys = list(oww_model.models.keys())
        print(f"Loaded active model keys: {loaded_keys}")
    except Exception as e:
        print(f"❌ Error loading openWakeWord model session: {e}")
        sys.exit(1)

    print("\nStarting live microphone monitoring...")
    print("Speak 'Sherlock', 'Hey Jarvis', or 'Alexa' into your microphone.")
    print("Press Ctrl+C to stop and view diagnostic summary.\n")
    print(f"{'Volume Level':<16} | {'sherlock.onnx':<15} | {'hey_jarvis':<15} | {'alexa':<15}")
    print("-" * 70)

    max_vol = 0
    max_sherlock = 0.0
    max_jarvis = 0.0
    max_alexa = 0.0
    chunk_size = 1280

    try:
        with sd.InputStream(samplerate=16000, channels=1, dtype="int16") as stream:
            while True:
                chunk, overflow = stream.read(chunk_size)
                audio_frame = np.frombuffer(chunk, dtype=np.int16)
                vol = int(np.abs(audio_frame).max())

                prediction = oww_model.predict(audio_frame)

                sherlock_score = extract_score(prediction, "sherlock")
                jarvis_score = extract_score(prediction, "hey_jarvis")
                alexa_score = extract_score(prediction, "alexa")

                if vol > max_vol:
                    max_vol = vol
                if sherlock_score > max_sherlock:
                    max_sherlock = sherlock_score
                if jarvis_score > max_jarvis:
                    max_jarvis = jarvis_score
                if alexa_score > max_alexa:
                    max_alexa = alexa_score

                vol_bar = "█" * min(8, int(vol / 1000))
                print(
                    f"\r{vol:5d} [{vol_bar:<8}] | {sherlock_score:13.4f} | {jarvis_score:13.4f} | {alexa_score:13.4f}",
                    end="",
                    flush=True,
                )
                time.sleep(0.02)
    except KeyboardInterrupt:
        print("\n\n" + "=" * 65)
        print("               DIAGNOSTIC TEST SUMMARY")
        print("=" * 65)
        print(f"Peak Microphone Audio Volume: {max_vol:<6} / 32767")
        print(f"Max 'sherlock.onnx' Score:   {max_sherlock:.4f}")
        print(f"Max 'hey_jarvis' Score:      {max_jarvis:.4f}")
        print(f"Max 'alexa' Score:           {max_alexa:.4f}")
        print("=" * 65)
        
        if max_vol < 1000:
            print("\n⚠️ WARNING: Microphone audio level was extremely low (< 1000). Check Windows microphone gain/input device.")
        elif max_sherlock < 0.15:
            print("\n⚠️ RESULT: 'sherlock.onnx' produced very low scores (< 0.15) even when speaking.")
            print("   This indicates 'sherlock.onnx' may be under-trained, over-fitted, or trained on mismatched audio features.")
        else:
            print(f"\n✅ RESULT: 'sherlock.onnx' reached a peak score of {max_sherlock:.4f}.")
            print(f"   Recommended threshold for main.py: {max(0.10, round(max_sherlock * 0.7, 2))}")

if __name__ == "__main__":
    main()
