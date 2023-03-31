import sys
import os
import discord
from io import BytesIO

sys.path.append(os.path.dirname(__file__))
import voicevox

DISCORD_AUTH_TOKEN = os.environ['DISCORD_AUTH_TOKEN']

voicevox_speaker_id = 3
voicevox.initialize(speaker_id=voicevox_speaker_id)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# https://discordpy.readthedocs.io/en/stable/api.html?highlight=intents#discord.Intents
# https://discordpy.readthedocs.io/en/stable/api.html?highlight=intents#voice-related
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    # print(f'We have logged in as {client.user}')
    pass


@client.event
async def on_voice_state_update(message, before, after):
    # print(message)
    pass


@client.event
async def on_message(message):
    print(message)
    if (message.channel.id == 1069237390671106113):
        if message.content == 'ON':
            await message.author.voice.channel.connect()
        elif message.content == 'OFF':
            await message.guild.voice_client.disconnect()
        else:
            text = message.content
            raw_pcm = voicevox.text_to_speech(text=text, speaker_id=voicevox_speaker_id, return_raw_pcm=True)

            audio_base_stream = BytesIO()
            audio_base_stream.write(raw_pcm)
            audio_base_stream.seek(0)

            audio_source = discord.PCMVolumeTransformer(
                # MARK: `volume` does not works for me.
                discord.PCMAudio(audio_base_stream), volume=1.0
            )
            message.guild.voice_client.play(audio_source)


if __name__ == '__main__':
    client.run(DISCORD_AUTH_TOKEN)
