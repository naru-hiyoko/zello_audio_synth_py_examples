import subprocess
import numpy as np
import pyvcroid2

from subprocess import PIPE


def initialize(speaker_name='akari_44'):
    vroid = pyvcroid2.VcRoid2()
    vroid.loadLanguage('standard')
    vroid.loadVoice(speaker_name)
    return vroid


def text_to_speech(text: str, vroid: pyvcroid2.VcRoid2) -> bytes:
    speech_bytes, _tts_evenets = vroid.textToSpeech(text, raw=True)
    pcm_data = np.frombuffer(speech_bytes, np.int16)

    # debug purpose
    # wavfile.write('sample44_1khz.wav', 44100, pcm_data)
    # _sample_rate, pcm_data = wavfile.read('sample44_1khz.wav')

    # windows -> linux/macos
    # pcm_data.tobytes()

    # wavfile.write('sample44_1khz.wav', 44100, pcm_data)
    # opusenc --raw --raw-bits 16 --raw-rate 44100 --raw-chan 1 --raw-endianness 0 sample.wav sample.opus

    p = subprocess.Popen('sox -b 16 -e signed -c 1 -r 44100 -t raw - -r 48000 -t wav - | opusenc --quiet - -',
                         stdin=PIPE, stdout=PIPE, shell=True)

    opus_data = p.communicate(pcm_data.tobytes())[0]
    return opus_data
