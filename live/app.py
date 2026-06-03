import os
import asyncio
import json
import base64
import logging
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from google import genai
from google.genai import types

# 設定日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gemini-live-backend")

app = FastAPI(title="Gemini Live 語音對話系統")

# 確保目錄存在
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

MODEL = "models/gemini-3.1-flash-live-preview"

# 預設語音設定
DEFAULT_VOICE = "Zephyr" # 預設語音：Zephyr, Puck, Charon, Kore, Fenrir 等

@app.get("/")
async def get_index():
    """首頁路由，直接回傳 index.html"""
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>index.html 未找到，請等待系統建置中...</h1>")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端點，作為瀏覽器前端與 Gemini Live API 之間的雙向橋樑。
    """
    await websocket.accept()
    logger.info("瀏覽器 WebSocket 已連線。")

    gemini_session = None
    client = None
    gemini_receive_task = None
    gemini_send_task = None
    
    # 建立一個佇列，用於存放要發送給 Gemini 的資料
    # 這可以避免多個 async task 寫入 session 造成競爭
    to_gemini_queue = asyncio.Queue()

    try:
        # 1. 第一步：等待前端發送設定訊息（含 API Key、模式與可選的舊工作階段 handle）
        setup_data = await websocket.receive_text()
        setup_json = json.loads(setup_data)
        
        if setup_json.get("type") != "setup":
            await websocket.send_json({"type": "error", "message": "首條訊息必須為 setup 設定。"})
            await websocket.close()
            return
            
        api_key = setup_json.get("api_key")
        video_mode = setup_json.get("video_mode", "none")
        voice_name = setup_json.get("voice_name", DEFAULT_VOICE)
        session_handle = setup_json.get("session_handle")
        history = setup_json.get("history", [])
        
        if not api_key:
            await websocket.send_json({"type": "error", "message": "缺少 API Key。"})
            await websocket.close()
            return
            
        logger.info(f"正在連線至 Gemini Live API... 模式: {video_mode}, 語音: {voice_name}, 歷史紀錄條數: {len(history)}")
        await websocket.send_json({"type": "status", "status": "connecting", "message": "正在建立與 Google AI Studio 的 Live 連線..."})

        # 2. 建立 Gemini 客戶端
        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )
        
        # 3. 根據對話歷史動態配置 system_instruction，讓 Developer API 也能完美記憶上下文
        base_instruction = "你是一個親切的中文語音助理。請務必使用繁體中文（台灣）與使用者進行語音交談，並用繁體中文回答所有問題。答話請保持精簡、口語，符合日常交談習慣，不要使用長篇大論的書面語。"
        
        if history:
            history_lines = []
            for turn in history:
                role_name = "使用者" if turn.get("role") == "user" else "助理"
                txt = turn.get("text", "")
                if txt:
                    history_lines.append(f"{role_name}：{txt}")
            
            history_context = "\n".join(history_lines)
            system_instruction = (
                f"{base_instruction}\n\n"
                f"【注意】以下是我們在連線中斷前進行的對話歷史紀錄，請牢記這些上下文，並在接下來的對話中無縫延續，但不要主動重複這些對話或在此時立刻發聲回應：\n"
                f"{history_context}"
            )
            logger.info("已成功為連線工作階段注入歷史對話上下文記憶。")
        else:
            system_instruction = base_instruction

        # 3. 配置 Live 連線設定
        config = types.LiveConnectConfig(
            response_modalities=[
                "AUDIO", # 我們需要 Gemini 回應語音
            ],
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=104857,
                sliding_window=types.SlidingWindow(target_tokens=52428),
            ),
            system_instruction=system_instruction,
            output_audio_transcription=types.AudioTranscriptionConfig()
        )

        # 4. 連線至 Gemini Live 服務
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            gemini_session = session
            logger.info("Gemini Live 連線成功！")
            await websocket.send_json({"type": "status", "status": "connected", "message": "連線成功！開始進行語音對話吧。"})

            # 定義接收 Gemini 回應並轉發給瀏覽器的任務
            async def receive_from_gemini():
                try:
                    # 關鍵修復：官方 SDK 的 session.receive() 在一次對話回合 (turn_complete) 結束後會主動 break 退出。
                    # 我們必須使用 while True 迴圈，在每回合結束後自動重新呼叫 session.receive() 監聽下一回合，
                    # 這樣就能實現真正的「單次連線、不間斷多輪對話」，徹底根治原先回答一次就斷線重連的異常！
                    while True:
                        async for response in session.receive():
                            # A. 處理音訊輸出
                            if response.data:
                                # 24kHz PCM 音訊，直接以 binary 格式發送給前端
                                await websocket.send_bytes(response.data)
                            
                            # B. 處理文字逐字稿 (優化：遍歷 parts 避免直接呼叫 response.text 觸發警告)
                            if response.server_content:
                                # 優先嘗試從 output_transcription 獲取語音逐字稿
                                if response.server_content.output_transcription and response.server_content.output_transcription.text:
                                    await websocket.send_json({"type": "text", "text": response.server_content.output_transcription.text})
                                
                                # 保留原先從 model_turn 獲取文字的邏輯做為 fallback
                                if response.server_content.model_turn:
                                    for part in response.server_content.model_turn.parts:
                                        if part.text:
                                            await websocket.send_json({"type": "text", "text": part.text})
                            
                            # D. 處理打斷機制 (Interruption)
                            if response.server_content is not None:
                                if getattr(response.server_content, "interrupted", False):
                                    logger.info("偵測到語音被打斷，發送 interrupt 指令給瀏覽器。")
                                    await websocket.send_json({"type": "interrupt"})
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"從 Gemini 接收資料時出錯: {str(e)}")
                    await websocket.send_json({"type": "error", "message": f"接收 Gemini 回應失敗: {str(e)}"})

            # 定義發送資料給 Gemini 的任務 (從佇列讀取)
            async def send_to_gemini():
                try:
                    while True:
                        item, end_of_turn = await to_gemini_queue.get()
                        item_type = item["type"]
                        item_data = item["data"]
                        
                        if item_type == "audio":
                            # 使用新版 send_realtime_input 發送音訊，並明確指定採樣率為 16000Hz
                            await session.send_realtime_input(
                                audio=types.Blob(data=item_data, mime_type="audio/pcm;rate=16000")
                            )
                        elif item_type == "video":
                            # 使用新版 send_realtime_input 發送影格
                            await session.send_realtime_input(
                                video=types.Blob(data=item_data, mime_type="image/jpeg")
                            )
                        elif item_type == "text":
                            # 使用新版 send_client_content 傳送對話文字並觸發回應
                            await session.send_client_content(
                                turns={"parts": [{"text": item_data}]},
                                turn_complete=True
                            )
                        to_gemini_queue.task_done()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"發送資料至 Gemini 時出錯: {str(e)}")
                    traceback.print_exc()
            # 定義接收瀏覽器資料的任務 (整合進 lifecycle 中)
            async def receive_from_browser():
                received_packet_count = 0
                try:
                    while True:
                        message = await websocket.receive()
                        
                        # 處理 Starlette ASGI 斷開連接事件
                        if message.get("type") == "websocket.disconnect":
                            logger.info(f"瀏覽器 WebSocket 已中斷，代碼: {message.get('code', '未知')}")
                            break
                        
                        # A. 處理 binary 訊息 (麥克風 PCM 16kHz 音訊)
                        if "bytes" in message:
                            pcm_data = message["bytes"]
                            received_packet_count += 1
                            if received_packet_count % 100 == 0:
                                logger.info(f"已從瀏覽器接收 100 個音訊封包，每個大小: {len(pcm_data)} 位元組 (累積封包: {received_packet_count})")
                            await to_gemini_queue.put(({"type": "audio", "data": pcm_data}, False))
                        
                        # B. 處理 text 訊息 (設定/視訊/文字輸入)
                        elif "text" in message:
                            try:
                                data = json.loads(message["text"])
                                msg_type = data.get("type")
                                
                                # 處理視訊影格
                                if msg_type == "video":
                                    base64_data = data.get("data")
                                    if base64_data:
                                        img_bytes = base64.b64decode(base64_data)
                                        await to_gemini_queue.put(({"type": "video", "data": img_bytes}, False))
                                        
                                # 處理前端發送的文字輸入 (純文字對話)
                                elif msg_type == "text":
                                    text_content = data.get("text")
                                    if text_content:
                                        await to_gemini_queue.put(({"type": "text", "data": text_content}, True))
                                        
                            except json.JSONDecodeError:
                                logger.warning("收到無效的 JSON 訊息。")
                except asyncio.CancelledError:
                    pass

            # 建立三個非同步任務，建立共同生命週期
            browser_task = asyncio.create_task(receive_from_browser(), name="BrowserReceiver")
            gemini_receive_task = asyncio.create_task(receive_from_gemini(), name="GeminiReceiver")
            gemini_send_task = asyncio.create_task(send_to_gemini(), name="GeminiSender")

            # 等待任何一個任務結束（例如 Google 連線中斷，或是瀏覽器斷開）
            done, pending = await asyncio.wait(
                [browser_task, gemini_receive_task, gemini_send_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 記錄導致結束的任務狀況
            for task in done:
                task_name = task.get_name()
                if task.exception():
                    logger.error(f"任務 [{task_name}] 異常終止: {task.exception()}")
                    # 印出異常詳細 Traceback
                    tb = task.exception().__traceback__
                    traceback.print_exception(type(task.exception()), task.exception(), tb)
                else:
                    logger.info(f"任務 [{task_name}] 已正常結束。")

            # 取消其他尚未結束的任務，確保資源被乾淨釋放與關閉
            for task in pending:
                task.cancel()
                
    except WebSocketDisconnect:
        logger.info("瀏覽器 WebSocket 連線已中斷。")
    except Exception as e:
        logger.error(f"伺服器運作錯誤: {str(e)}")
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": f"連線錯誤: {str(e)}"})
        except:
            pass
    finally:
        # 清除所有背景任務
        if gemini_receive_task:
            gemini_receive_task.cancel()
        if gemini_send_task:
            gemini_send_task.cancel()
        
        # 確保關閉與瀏覽器的連線
        try:
            await websocket.close()
        except:
            pass
        logger.info("已清理連線資源。")

# 掛載靜態資源目錄
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    logger.info("啟動語音對話本地服務於 http://localhost:8088 ...")
    uvicorn.run(app, host="127.0.0.1", port=8088)
