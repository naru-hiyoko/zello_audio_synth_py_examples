import os
import asyncio
import aiohttp
import subprocess
import numpy as np
import json
import time
import logging
import base64

from aiohttp import TCPConnector, ClientSession, WSMsgType
from socket import AF_INET
# from scipy.io import wavfile
from opus_file_stream import OpusStream

ZELLO_WEB_SOCKET_URL = 'wss://zello.io/ws'
ZELLO_AUTH_TOKEN = os.environ['ZELLO_AUTH_TOKEN']
ZELLO_TIMEOUT_SEC = 1


def opus_packets(opus_data: bytes, stream_id: int):
    opus_stream = OpusStream(opus_data)
    packet_id = 0

    while True:
        opus_packet_data = opus_stream.get_next_opus_packet()

        if not opus_packet_data:
            break

        packet_id += 1
        packet = (1).to_bytes(1, "big") + stream_id.to_bytes(4, "big") + \
            packet_id.to_bytes(4, "big") + opus_packet_data
        yield packet


class Client:
    def __init__(self):
        self.logger = logging.getLogger('zello')
        self.connector = TCPConnector(family=AF_INET, ssl=False)
        self.session = ClientSession(connector=self.connector)
        self.ws = None
        self.is_authorized = False
        self.seq = 0

    async def close(self):
        if self.ws:
            await self.ws.close()

        await self.session.close()

    async def connect(self):
        self.ws = await self.session.ws_connect(ZELLO_WEB_SOCKET_URL)

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None

    def message_as_dict(self, message):
        """
        convert json message from ws to dict.
        """
        if message.type == WSMsgType.TEXT:
            return json.loads(message.data)
        elif message.type == WSMsgType.BINARY:
            # message.data
            return {}
        else:
            self.logger.warning(message)
            return {}

    async def recv_message(self):
        async for message in self.ws:
            result = self.message_as_dict(message)
            self.logger.info(result)
            return result

    async def logon(self, username, password, channel):
        if self.seq != 0:
            return
        else:
            self.seq += 1

        # https://github.com/zelloptt/zello-channel-api/blob/master/AUTH.md
        await self.ws.send_str(json.dumps({
            "command": "logon",
            "seq": 1,
            "auth_token": ZELLO_AUTH_TOKEN,
            "username": username,
            "password": password,
            "channel": channel
        }))

        is_channel_available = None
        async for message in self.ws:
            result = self.message_as_dict(message)
            self.logger.info(result)

            if "refresh_token" in result:
                self.is_authorized = True
            elif "command" in result and "status" in result and result["command"] == "on_channel_status":
                is_channel_available = result["status"] == "online"

            if (self.is_authorized is not None) and (is_channel_available is not None):
                break

        if not self.is_authorized or not is_channel_available:
            raise NameError('Authentication failed.')

        else:
            self.logger.info('Authentication success.')

    async def start_stream(self) -> int:
        """
        Returns: stream_id
        """
        self.seq += 1

        sample_rate = 48000
        frames_per_packet = 1
        packet_duration = 20

        # Sample_rate is in little endian.
        # https://github.com/zelloptt/zello-channel-api/blob/409378acd06257bcd07e3f89e4fbc885a0cc6663/sdks/js/src/classes/utils.js#L63
        codec_header = base64.b64encode(sample_rate.to_bytes(2, "little") + \
            frames_per_packet.to_bytes(1, "big") + packet_duration.to_bytes(1, "big")).decode()

        await self.ws.send_str(json.dumps({
            "command": "start_stream",
            "seq": self.seq,
            "type": "audio",
            "codec": "opus",
            "codec_header": codec_header,
            "packet_duration": packet_duration
        }))

        async for message in self.ws:
            result = self.message_as_dict(message)
            if "success" in result and "stream_id" in result and result["success"]:
                return result["stream_id"]
            elif "error" in result:
                self.logger.error(result['error'])
                raise NameError('Failed to create zello audio stream')
            else:
                # Ignore the messages we are not interested in
                self.logger.warning(result)
                continue

    async def stop_stream(self, stream_id: int):
        await self.ws.send_str(json.dumps({
            "command": "stop_stream",
            "stream_id": stream_id
        }))

    async def send_audio_stream(self, opus_data: bytes, stream_id: int):
        packet_duration_sec = 20 / 1000
        start_ts_sec = time.time_ns() / 1000000000
        time_streaming_sec = 0

        for packet in opus_packets(opus_data, stream_id=stream_id):
            await self.ws.send_bytes(packet)

            time_streaming_sec += packet_duration_sec
            time_elapsed_sec = (time.time_ns() / 1000000000) - start_ts_sec
            sleep_delay_sec = time_streaming_sec - time_elapsed_sec

            if sleep_delay_sec > 0.001:
                time.sleep(sleep_delay_sec)
