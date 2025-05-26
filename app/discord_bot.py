import os
import discord
import aiohttp
import asyncio
from core.config import DISCORD_TOKEN, FASTAPI_URL, OUTPUT_DIR, OUTPUT_3D_DIR, MVADAPTER_SERVER, HY3D_SERVER, PROMPT_CONVERT_API

os.makedirs(OUTPUT_3D_DIR, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # ✅ 유지: SFX 생성 처리
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
                    if not isinstance(positive_list, list) or not positive_list:
                        await message.channel.send("❌ 변환된 프롬프트가 비어 있음")
                        return
                    prompt = ", ".join(positive_list)

            await message.channel.send(f"🖌️ 변환된 프롬프트: {prompt}")
            await message.channel.send("🖼️ 이미지 생성 중...")

            # ✅ 1. /generate 호출
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{MVADAPTER_SERVER}/generate",
                    json={"user_prompt": prompt, "user_negative": "low quality, shadow"}
                ) as resp:
                    if resp.status != 200:
                        await message.channel.send("❌ 이미지 생성 실패 (/generate)")
                        return

            await asyncio.sleep(2)

            # ✅ 2. 생성된 PNG 중 가장 최신 파일을 MVAdapter reference로 사용
            image_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".png")]
            if not image_files:
                await message.channel.send("❌ 생성된 PNG 파일이 없습니다.")
                return

            reference_filename = sorted(image_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)))[-1]
            print(f"[DEBUG] reference_filename for MVAdapter: {reference_filename}")

            # ✅ 3. MVAdapter 실행
            await message.channel.send("🎨 텍스처 이미지 생성 중...")
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

            # ✅ 4. 텍스처 이미지 탐색
            tex_imgs = find_latest_named_images(OUTPUT_DIR, ["front", "back", "left"])
            if not all(tex_imgs.values()):
                await message.channel.send("❌ front/back/left 텍스처 이미지 누락")
                return

            # ✅ 5. GLB 생성
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

client.run(DISCORD_TOKEN)
