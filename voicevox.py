import requests
import subprocess

from subprocess import PIPE

BASE_URL = 'http://127.0.0.1:50021'


def initialize(speaker_id):
    resp = requests.post(f'{BASE_URL}/initialize_speaker?speaker={speaker_id}', data={})
    assert resp.status_code == 204, '初期化に失敗しました。'
    return None


def text_to_speech(text, speaker_id, return_raw_pcm = False):
    # TODO: remove a `vroid` argument.

    resp = requests.post(f'{BASE_URL}/audio_query', params=dict(
        speaker=speaker_id,
        text=text,
    ))

    assert resp.status_code == 200
    audio_query = resp.content

    resp = requests.post(f'{BASE_URL}/synthesis', params=dict(speaker=speaker_id), data=audio_query)
    assert resp.status_code == 200
    wav_data = resp.content

    if return_raw_pcm:
        p = subprocess.Popen('sox -b 16 -e signed -c 1 -r 24000 -t raw - -b 16 -e signed -c 2 -r 48000 -t wav -',
                             stdin=PIPE, stdout=PIPE, shell=True)

        raw_pcm = p.communicate(wav_data)[0]
        return raw_pcm
    else:
        p = subprocess.Popen('sox -b 16 -e signed -c 1 -r 24000 -t raw - -r 48000 -t wav - | opusenc --quiet - -',
                             stdin=PIPE, stdout=PIPE, shell=True)

        opus_data = p.communicate(wav_data)[0]
        return opus_data