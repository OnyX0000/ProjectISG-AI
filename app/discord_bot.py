import os
import discord
import aiohttp
from core.config import DISCORD_TOKEN, FASTAPI_URL

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!sfx "):
        try:
            content = message.content[5:].strip()
            parts = [p.strip() for p in content.split(",")]

            prompt = parts[0]
            duration = parts[1] if len(parts) > 1 else None
            prompt_influence = parts[2] if len(parts) > 2 else "0.3"

            # ✅ 문자열 그대로 전달
            query_params = {
                "prompt": prompt,
                "prompt_influence": prompt_influence
            }
            if duration:
                query_params["duration"] = duration

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    FASTAPI_URL,
                    params=query_params
                ) as response:
                    if response.status == 200:
                        cd = response.headers.get("Content-Disposition", "")
                        filename = "sfx_result.mp3"
                        if "filename=" in cd:
                            filename = cd.split("filename=")[-1].strip('"')

                        with open(filename, "wb") as f:
                            f.write(await response.read())

                        await message.channel.send(
                            content=f"🎵 SFX 생성 완료: {prompt}",
                            file=discord.File(filename)
                        )

                        os.remove(filename)
                    else:
                        await message.channel.send("❌ SFX 생성 실패")

        except Exception as e:
            await message.channel.send(f"❌ 오류 발생: {e}")

client.run(DISCORD_TOKEN)
