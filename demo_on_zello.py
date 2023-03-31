import sys
import os
import argparse
import asyncio
import logging

sys.path.append(os.path.dirname(__file__))

import voicevox
from zello import Client as ZelloClient

global event_loop

async def app(args, logger):
    voicevox_speaker_id = 3
    voicevox.initialize(speaker_id=voicevox_speaker_id)

    zello_client = ZelloClient()
    await zello_client.connect()

    logger.info('Connection established.')

    try:
        await zello_client.logon(args.username, args.password, args.channel)
        while True:
            msg = await zello_client.recv_message()
            if 'command' in msg and msg['command'] == 'on_text_message':
                text = msg['text']
                opus_data = voicevox.text_to_speech(text=text, speaker_id=voicevox_speaker_id)

                stream_id = await zello_client.start_stream()
                await zello_client.send_audio_stream(opus_data, stream_id=stream_id)
                await zello_client.stop_stream(stream_id)

    except Exception as e:
        logger.error(e)

    finally:
        await zello_client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Send audio from discord message to zello app.')

    # config for consumer zello.
    parser.add_argument('--username', type=str, required=True, help='zello account name')
    parser.add_argument('--password', type=str, required=True, help='password for zello account')
    parser.add_argument('--channel', type=str, required=False, default='channel_4927', help='channel where you want to join')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format='{asctime} [{levelname:.4}] {name}: {message}', style='{')

    logger = logging.getLogger('app')

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(
        app(args, logger)
    )
    event_loop.close()
