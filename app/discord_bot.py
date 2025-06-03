import os
import discord
import aiohttp
import asyncio
from datetime import datetime
from core.config import (
    DISCORD_TOKEN, FASTAPI_URL,
    OUTPUT_DIR, OUTPUT_3D_DIR,
    MVADAPTER_SERVER, HY3D_SERVER,
    PROMPT_CONVERT_API, SUPERTONEAI_API_KEY
)

os.makedirs(OUTPUT_3D_DIR, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

last_help_time = None
help_channel = None

def get_random_hex():
    return os.urandom(8).hex()

def find_latest_named_images(folder, name_keys):
    result = {}
    for key in name_keys:
        files = [f for f in os.listdir(folder) if key in f and f.endswith(".png")]
        if not files:
            result[key] = None
        else:
            result[key] = max(files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    return result

def help_message_text():
    return (
        "📦 [ASSET 생성 에이전트 명령어 요약]\n\n"
        "**🎵 !sfx** `<프롬프트>[, 길이: 0.5~22.0][, 가중치: 0.0~1.0]`\n"
        "예: `!sfx 파도 소리, 3.0, 0.7`\n\n"
        "**🧊 !3d** `<프롬프트>`\n"
        "예: `!3d 나무로 만든 작은 의자`\n\n"
        "**🗣️ !tts** `<문장>, <voice_id>, <언어>, <스타일>[, pitch, variance, speed]`\n"
        "- pitch: -2.0 ~ 2.0 (기본 0.0)\n"
        "- variance: 0.0 ~ 1.0 (기본 1.0)\n"
        "- speed: 0.5 ~ 2.0 (기본 1.0)\n"
        "- `voice_id`는 **!voice**로 조회\n"
        "예: `!tts 집에 보내주세요 제발, aiko, ko, angry`\n\n"
        "**📢 !voice** `<언어>[ key=value ... ]`\n"
        "- 예: `!voice ko gender=female`, `!voice en age=young-adult`\n"
        "- voice_id, 스타일, 언어, 나이, 이름, 성별, voice_id 등을 조회 가능\n"
    )

# @client.event
# async def on_ready():
#     global help_channel, last_help_time
#     print(f"✅ Logged in as {client.user}")
#     help_channel = discord.utils.get(client.get_all_channels(), name="asset_생성")  # 메시지를 보낼 채널
#     if help_channel:
#         await help_channel.send(help_message_text())
#         last_help_time = datetime.utcnow()
#         asyncio.create_task(periodic_help_sender())

async def periodic_help_sender():
    global last_help_time, help_channel
    await client.wait_until_ready()

    while not client.is_closed():
        now = datetime.utcnow()
        if help_channel and now.minute == 0 and now.second < 5:
            if not last_help_time or (now - last_help_time).total_seconds() >= 3600:
                try:
                    await help_channel.send(help_message_text())
                    last_help_time = now
                except Exception as e:
                    print(f"[ERROR] 도움말 전송 실패: {e}")

        seconds_until_next_hour = 3600 - (now.minute * 60 + now.second)
        await asyncio.sleep(min(60, seconds_until_next_hour))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.strip() == "!help":
        await message.channel.send(help_message_text())
        return

    # ✅ SFX 생성 처리
    if message.content.startswith("!sfx "):
        try:
            content = message.content[5:].strip()
            parts = [p.strip() for p in content.split(",")]
            prompt = parts[0]
            duration = parts[1] if len(parts) > 1 else None
            prompt_influence = parts[2] if len(parts) > 2 else "0.3"

            query_params = {
                "prompt": prompt,
                "prompt_influence": prompt_influence
            }
            if duration:
                query_params["duration"] = duration

            async with aiohttp.ClientSession() as session:
                async with session.post(FASTAPI_URL, params=query_params) as response:
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

    # ✅ 3D 생성 처리
    elif message.content.startswith("!3d "):
        try:
            user_kor_prompt = message.content[4:].strip()
            if not user_kor_prompt:
                await message.channel.send("❗ 프롬프트를 입력하세요. 예: !3d 작은 나무 의자")
                return

            await message.channel.send(f"🌐 프롬프트 변환 중: {user_kor_prompt}")
            async with aiohttp.ClientSession() as session:
                async with session.post(PROMPT_CONVERT_API, params={"prompt": user_kor_prompt}) as resp:
                    if resp.status != 200:
                        await message.channel.send("❌ 프롬프트 변환 실패")
                        return
                    result = await resp.json()
                    positive_list = result.get("prompts", {}).get("positive", [])
                    negative_list = result.get("prompts", {}).get("negative", [])
                    if not isinstance(positive_list, list) or not positive_list:
                        await message.channel.send("❌ 변환된 프롬프트가 비어 있음")
                        return
                    prompt = ", ".join(positive_list)
                    negative = ", ".join(negative_list) if isinstance(negative_list, list) else "low quality"

            await message.channel.send(f"🖌️ 변환된 프롬프트: {prompt}")
            await message.channel.send("🖼️ 이미지 생성 중...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{MVADAPTER_SERVER}/generate",
                    json={"user_prompt": prompt, "user_negative": negative}
                ) as resp:
                    if resp.status != 200:
                        await message.channel.send("❌ 이미지 생성 실패 (/generate)")
                        return

            await asyncio.sleep(2)

            image_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".png")]
            if not image_files:
                await message.channel.send("❌ 생성된 PNG 파일이 없습니다.")
                return

            reference_filename = sorted(image_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)))[-1]
            reference_path = os.path.join(OUTPUT_DIR, reference_filename)

            await message.channel.send("🎨 텍스처 이미지 생성 중...", file=discord.File(reference_path))

            async with aiohttp.ClientSession() as session:
                mv_payload = {
                    "reference_filename": reference_filename,
                    "user_prompt": prompt
                }
                async with session.post(f"{MVADAPTER_SERVER}/generate_mv_adapter", json=mv_payload) as resp:
                    if resp.status != 200:
                        await message.channel.send("❌ MVAdapter 텍스처 생성 실패")
                        return

            await asyncio.sleep(5)

            tex_imgs = find_latest_named_images(OUTPUT_DIR, ["front", "back", "left"])
            if not all(tex_imgs.values()):
                await message.channel.send("❌ front/back/left 텍스처 이미지 누락")
                return

            await message.channel.send("🧊 GLB 생성 중...")

            files = {
                "front": open(os.path.join(OUTPUT_DIR, tex_imgs["front"]), "rb"),
                "back": open(os.path.join(OUTPUT_DIR, tex_imgs["back"]), "rb"),
                "left": open(os.path.join(OUTPUT_DIR, tex_imgs["left"]), "rb")
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{HY3D_SERVER}/generate_hy3d", data=files) as resp:
                    for f in files.values():
                        f.close()
                    if resp.status != 200:
                        await message.channel.send(f"❌ GLB 생성 실패 (status: {resp.status})")
                        return
                    unique_filename = f"Hy3D_textured_{get_random_hex()}.glb"
                    glb_path = os.path.join(OUTPUT_3D_DIR, unique_filename)
                    with open(glb_path, "wb") as f:
                        f.write(await resp.read())

            await message.channel.send("✅ 3D 모델 생성 완료!", file=discord.File(glb_path))

        except Exception as e:
            await message.channel.send(f"❌ 3D 생성 중 오류 발생: {e}")

    # ✅ TTS 처리
    elif message.content.startswith("!tts "):
        try:
            content = message.content[5:].strip()
            parts = [p.strip() for p in content.split(",")]

            text = parts[0]
            voice_id = parts[1] if len(parts) > 1 else "91992bbd4758bdcf9c9b01"
            language = parts[2] if len(parts) > 2 else "ko"
            style = parts[3] if len(parts) > 3 else "neutral"
            model = parts[4] if len(parts) > 4 else "sona_speech_1"
            pitch_shift = float(parts[5]) if len(parts) > 5 else 0.0
            pitch_variance = float(parts[6]) if len(parts) > 6 else 1.0
            speed = float(parts[7]) if len(parts) > 7 else 1.0

            payload = {
                "text": text,
                "language": language,
                "style": style,
                "model": model,
                "voice_settings": {
                    "pitch_shift": pitch_shift,
                    "pitch_variance": pitch_variance,
                    "speed": speed
                }
            }

            headers = {
                "x-sup-api-key": SUPERTONEAI_API_KEY,
                "Content-Type": "application/json"
            }

            url = f"https://supertoneapi.com/v1/text-to-speech/{voice_id}?output_format=wav"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        await message.channel.send(f"❌ TTS 생성 실패 (status: {resp.status})\n{error_text}")
                        return

                    filename = "tts_output.mp3"
                    with open(filename, "wb") as f:
                        f.write(await resp.read())

                    await message.channel.send(f"✅ TTS 생성 완료: `{text}`", file=discord.File(filename))
                    os.remove(filename)

        except Exception as e:
            await message.channel.send(f"❌ 오류 발생: {e}")
    
    # ✅ TTS 목소리 목록 조회
    elif message.content.startswith("!voice"):
        try:
            # ✅ 메시지 파싱
            parts = message.content.strip().split()
            filters = {}

            # 첫 번째 파라미터: 언어 필터
            if len(parts) > 1:
                filters["language"] = parts[1]

            # 이후: key=value 형태 필터들
            for part in parts[2:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k in {"gender", "style", "age", "name"}:  # 허용된 필터만 추가
                        filters[k] = v

            # ✅ model은 고정값
            filters["model"] = "sona_speech_1"

            headers = {
                "x-sup-api-key": SUPERTONEAI_API_KEY,
                "Content-Type": "application/json"
            }

            url = "https://supertoneapi.com/v1/voices/search"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=filters) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        await message.channel.send(f"❌ Voice 목록 조회 실패 (status: {resp.status})\n{error_text}")
                        return

                    result = await resp.json()
                    voices = result.get("items", [])
                    if not voices:
                        await message.channel.send("⚠️ 사용할 수 있는 Voice가 없습니다.")
                        return

                    # ✅ 결과 출력
                    lines = ["📢 **[사용 가능한 Voice 목록]**\n"]
                    for v in voices[:10]:
                        lines.append(
                            f"- **{v.get('name', 'Unnamed')}**\n"
                            f"  - ID: `{v.get('voice_id')}`\n"
                            f"  - 언어: {', '.join(v.get('language', []))}\n"
                            f"  - 성별: {v.get('gender', 'Unknown')}\n"
                            f"  - 나이대: {v.get('age', 'Unknown')}\n"
                            f"  - 스타일: {', '.join(v.get('styles', []))}\n"
                            f"  - 모델: {', '.join(v.get('models', []))}\n"
                        )

                    await message.channel.send("\n".join(lines))

        except Exception as e:
            await message.channel.send(f"❌ 오류 발생: {e}")

client.run(DISCORD_TOKEN)
