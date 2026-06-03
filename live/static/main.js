/* ==========================================================================
   Gemini Live Web Voice Chat Client Logic (繁體中文版)
   ========================================================================== */

// DOM 元素參考
const apiKeyInput = document.getElementById("apiKey");
const toggleApiKeyBtn = document.getElementById("toggleApiKey");
const voiceModeSelect = document.getElementById("voiceMode");
const voiceSelect = document.getElementById("voiceSelect");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const connectionTimer = document.getElementById("connectionTimer");
const videoPreviewWrapper = document.getElementById("videoPreviewWrapper");
const localVideo = document.getElementById("localVideo");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const muteMicBtn = document.getElementById("muteMicBtn");
const chatLog = document.getElementById("chatLog");
const textInput = document.getElementById("textInput");
const sendTextBtn = document.getElementById("sendTextBtn");

const userCanvas = document.getElementById("userCanvas");
const geminiCanvas = document.getElementById("geminiCanvas");

// VAD 靈敏度與重連 DOM 參考
const vadSlider = document.getElementById("vadSlider");
const vadValue = document.getElementById("vadValue");

// 全域狀態變數
let ws = null;
let audioCtx = null;
let micStream = null;
let micSource = null;
let scriptNode = null;
let videoStream = null;
let videoInterval = null;

let userAnalyser = null;
let geminiAnalyser = null;

let nextStartTime = 0;
let activeSources = [];
let isMuted = false;
let connStartTime = null;
let timerInterval = null;

// 自動重連與 Session Resumption 狀態
let reconnectAttempts = 0;
let isReconnecting = false;
const maxReconnectAttempts = 5;

// 最後發言的氣泡節點 (用於即時更新 Gemini 逐字稿)
let currentGeminiBubble = null;
let currentGeminiText = "";
let conversationHistory = []; // 用於保存對話歷史，在斷線重連時傳遞給 Gemini 以恢復記憶

function saveGeminiHistory() {
    if (currentGeminiText) {
        const trimmed = currentGeminiText.trim();
        if (trimmed) {
            // 避免重複加入相同的紀錄
            const lastTurn = conversationHistory[conversationHistory.length - 1];
            if (!lastTurn || lastTurn.text !== trimmed || lastTurn.role !== "model") {
                conversationHistory.push({ role: "model", text: trimmed });
                console.log("已將 Gemini 回應存入歷史紀錄:", trimmed);
            }
        }
        currentGeminiText = "";
    }
}

// 1. 初始化與 API Key 讀取
window.addEventListener("DOMContentLoaded", () => {
    // 嘗試從 LocalStorage 讀取已保存的 API Key
    const savedKey = localStorage.getItem("gemini_live_api_key");
    if (savedKey) {
        apiKeyInput.value = savedKey;
    }
    
    // 讀取/儲存已保存的 VAD 靜音門檻
    const savedVad = localStorage.getItem("gemini_live_vad_threshold");
    if (savedVad && vadSlider && vadValue) {
        vadSlider.value = savedVad;
        vadValue.innerText = parseFloat(savedVad).toFixed(3);
    }

    if (vadSlider) {
        vadSlider.addEventListener("input", () => {
            const val = parseFloat(vadSlider.value);
            if (vadValue) {
                vadValue.innerText = val.toFixed(3);
            }
            localStorage.setItem("gemini_live_vad_threshold", val.toString());
        });
    }

    // 重置舊的 Session Handle 防止跨開啟對話干擾
    localStorage.removeItem("gemini_live_session_handle");
    
    // API Key 顯示/隱藏切換
    toggleApiKeyBtn.addEventListener("click", () => {
        if (apiKeyInput.type === "password") {
            apiKeyInput.type = "text";
            toggleApiKeyBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
        } else {
            apiKeyInput.type = "password";
            toggleApiKeyBtn.innerHTML = '<i class="fa-solid fa-eye"></i>';
        }
    });

    // 模式選擇改變時，更新視訊預覽框顯示
    voiceModeSelect.addEventListener("change", () => {
        const mode = voiceModeSelect.value;
        if (mode !== "none" && ws && ws.readyState === WebSocket.OPEN) {
            // 如果已連線，動態重啟視訊串流
            stopVideoInput();
            startVideoInput(mode);
        } else {
            videoPreviewWrapper.style.display = mode !== "none" ? "block" : "none";
        }
    });

    // 設定 Canvas 尺寸以獲得高解析度繪圖
    resizeCanvas(userCanvas);
    resizeCanvas(geminiCanvas);
    window.addEventListener("resize", () => {
        resizeCanvas(userCanvas);
        resizeCanvas(geminiCanvas);
    });

    // 啟動視覺化繪圖迴圈
    drawVisualizers();
});

// 2. 視窗 Canvas 自適應
function resizeCanvas(canvas) {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = 100;
}

// 3. 連線與自動重連處理
connectBtn.addEventListener("click", () => {
    connect(false);
});

async function connect(isReconnect = false) {
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
        alert("請輸入您的 Google AI Studio API Key。");
        apiKeyInput.focus();
        return;
    }

    // 儲存金鑰至本地
    localStorage.setItem("gemini_live_api_key", apiKey);

    if (!isReconnect) {
        // 全新連線，重設重連狀態與歷史
        reconnectAttempts = 0;
        isReconnecting = false;
        conversationHistory = []; // 清空前一次手動對話歷史
        chatLog.innerHTML = "";
        addLogMessage("正在初始化音訊與連線...", "info");
        setUIState("connecting");
        localStorage.removeItem("gemini_live_session_handle"); // 清除先前快取的工作階段
    } else {
        addLogMessage(`連線中斷，正在自動重新連線 (第 ${reconnectAttempts}/${maxReconnectAttempts} 次嘗試)...`, "connecting");
        setUIState("connecting");
    }

    try {
        // A. 初始化 Web Audio API
        await initAudio();
        
        // B. 請求麥克風授權並建立串流
        if (!micStream) {
            await startMicInput();
        }

        // C. 建立 WebSocket 連線
        const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        const wsUrl = `${protocol}${window.location.host}/ws`;
        
        ws = new WebSocket(wsUrl);
        ws.binaryType = "arraybuffer";

        // WebSocket 開啟事件
        ws.onopen = () => {
            if (isReconnect) {
                addLogMessage("網路已恢復，對話工作階段重啟成功！", "connected");
            } else {
                addLogMessage("伺服器握手成功，正在傳送認證設定...", "info");
            }
            
            // 傳送第一條 Setup 訊息 (夾帶歷史紀錄與 session_handle 嘗試恢復記憶)
            const setupMsg = {
                type: "setup",
                api_key: apiKey,
                video_mode: voiceModeSelect.value,
                voice_name: voiceSelect.value,
                session_handle: localStorage.getItem("gemini_live_session_handle") || null,
                history: conversationHistory // 傳遞對話記憶
            };
            ws.send(JSON.stringify(setupMsg));
            
            // 重設重連旗標
            reconnectAttempts = 0;
            isReconnecting = false;
        };

        // WebSocket 接收訊息事件
        ws.onmessage = async (event) => {
            // I. 處理二進位資料 (Gemini 24kHz PCM 語音)
            if (event.data instanceof ArrayBuffer) {
                playPCM24kHz(event.data);
            } 
            // II. 處理文字 JSON 資料
            else {
                try {
                    const msg = JSON.parse(event.data);
                    
                    // A. 處理文字逐字稿
                    if (msg.type === "text") {
                        handleTextResponse(msg.text);
                    } 
                    // B. 處理語音打斷事件 (Interrupted)
                    else if (msg.type === "interrupt") {
                        handleInterruption();
                    } 
                    // C. 處理 Session Resumption Handle 更新
                    else if (msg.type === "session_handle") {
                        localStorage.setItem("gemini_live_session_handle", msg.handle);
                        console.log("儲存了新的 Session Resumption Handle: " + msg.handle.substring(0, 15) + "...");
                    }
                    // D. 處理狀態更新
                    else if (msg.type === "status") {
                        addLogMessage(msg.message, msg.status);
                        if (msg.status === "connected") {
                            setUIState("connected");
                            startTimer();
                            // 動態開啟相機或螢幕分享
                            startVideoInput(voiceModeSelect.value);
                        }
                    } 
                    // E. 處理錯誤訊息
                    else if (msg.type === "error") {
                        addLogMessage(`錯誤: ${msg.message}`, "error");
                        disconnect();
                    }
                } catch (e) {
                    console.error("解析 JSON 訊息失敗:", e);
                }
            }
        };

        // WebSocket 關閉事件
        ws.onclose = (event) => {
            console.log("WebSocket 連線關閉，代碼: " + event.code);
            
            // 判斷是否非主動斷線且有連線歷史，若是則觸發自動重連
            if (ws && !isReconnecting) {
                triggerAutoReconnect();
            } else if (!isReconnecting) {
                addLogMessage("連線已關閉。", "info");
                disconnect();
            }
        };

        // WebSocket 錯誤事件
        ws.onerror = (error) => {
            console.error("WebSocket 連線錯誤: ", error);
            // 連線錯誤通常會伴隨著 onclose，所以由 onclose 處理自動重連
        };

    } catch (err) {
        addLogMessage(`連線初始化失敗: ${err.message}`, "error");
        console.error(err);
        disconnect();
    }
}

// 4. 指數退避自動重連機制
function triggerAutoReconnect() {
    if (isReconnecting) return;
    isReconnecting = true;

    // 保存當前未結案的 Gemini 回應字詞到歷史紀錄
    saveGeminiHistory();

    // 清理舊的 Websocket 物件，以利重連
    if (ws) {
        try {
            ws.close();
        } catch (e) {}
        ws = null;
    }

    reconnectAttempts++;
    if (reconnectAttempts > maxReconnectAttempts) {
        addLogMessage("已達最大重連上限次數，停止重新連線。", "error");
        disconnect();
        return;
    }

    // 關鍵優化：第一波重連 (1st attempt) 使用極短延遲 (50ms) 以實現瞬間無縫重連；後續失敗則使用指數退避 (1s, 2s, 4s, 8s...)
    const delay = reconnectAttempts === 1 ? 50 : Math.pow(2, reconnectAttempts - 2) * 1000;
    if (delay > 50) {
        addLogMessage(`將在 ${delay / 1000} 秒後發起自動重連機制...`, "info");
    } else {
        addLogMessage(`連線意外中斷，正在立即發起無縫重新連線...`, "info");
    }

    setTimeout(async () => {
        // 如果在定時重連期間使用者點擊了「中斷連線」，則中斷重連
        if (!isReconnecting) return;
        
        isReconnecting = false;
        await connect(true);
    }, delay);
}

// 5. 中斷連線處理
disconnectBtn.addEventListener("click", () => {
    disconnect();
});

function disconnect() {
    // 保存當前未結案的 Gemini 回應字詞到歷史紀錄
    saveGeminiHistory();

    addLogMessage("正在中斷連線並清理資源...", "info");
    
    isReconnecting = false;
    reconnectAttempts = 0;
    localStorage.removeItem("gemini_live_session_handle"); // 清除工作階段
    
    // 關閉 WebSocket
    if (ws) {
        const tempWs = ws;
        ws = null; // 設為 null 可避免 onclose 重複調用 triggerAutoReconnect()
        if (tempWs.readyState === WebSocket.OPEN || tempWs.readyState === WebSocket.CONNECTING) {
            tempWs.close();
        }
    }

    // 關閉麥克風
    stopMicInput();

    // 關閉視訊
    stopVideoInput();

    // 停止語音播放
    interruptPlayback();

    // 停止計時器
    stopTimer();

    // 暫停音訊環境釋放硬體資源與防漏音
    if (audioCtx) {
        try {
            audioCtx.suspend();
        } catch (e) {
            console.error("Failed to suspend AudioContext:", e);
        }
    }

    // 重設 UI 狀態
    setUIState("disconnected");
    currentGeminiBubble = null;
    currentGeminiText = "";
}

// 5. 麥克風靜音切換
muteMicBtn.addEventListener("click", () => {
    isMuted = !isMuted;
    if (isMuted) {
        muteMicBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>';
        muteMicBtn.classList.remove("btn-secondary");
        muteMicBtn.classList.add("btn-danger");
        muteMicBtn.title = "取消靜音";
        addLogMessage("麥克風已靜音", "info");
    } else {
        muteMicBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        muteMicBtn.classList.remove("btn-danger");
        muteMicBtn.classList.add("btn-secondary");
        muteMicBtn.title = "靜音麥克風";
        addLogMessage("麥克風已開啟", "info");
    }
});

// 6. 輔助文字輸入傳送
sendTextBtn.addEventListener("click", sendTextMessage);
textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendTextMessage();
    }
});

function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    // 保存當前未結案的 Gemini 回應字詞到歷史紀錄
    saveGeminiHistory();

    // 儲存使用者的手動文字輸入到歷史紀錄
    conversationHistory.push({ role: "user", text: text });

    // 傳送給後端
    ws.send(JSON.stringify({
        type: "text",
        text: text
    }));

    // 在對話稿中加入使用者的發言
    addUserMessageBubble(text);
    textInput.value = "";
    
    // 中斷當前播放 (發送新指令時應立刻停下)
    interruptPlayback();
}

// 7. 音訊初始化 (Web Audio API)
async function initAudio() {
    if (audioCtx) {
        if (audioCtx.state === "suspended") {
            await audioCtx.resume();
        }
        return;
    }
    
    // 建立 16000Hz AudioContext，瀏覽器會以硬體級高品質抗混疊濾波器自動完成雙向重採樣，保證錄音清晰度！
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContextClass({ sampleRate: 16000 });
    
    // 建立使用者音訊分析節點 (Mic Visualizer)
    userAnalyser = audioCtx.createAnalyser();
    userAnalyser.fftSize = 256;
    
    // 建立 Gemini 音訊分析節點 (Gemini Visualizer)
    geminiAnalyser = audioCtx.createAnalyser();
    geminiAnalyser.fftSize = 256;
    geminiAnalyser.connect(audioCtx.destination);
}

// 8. 麥克風音訊擷取與原生高品質 16kHz PCM 編碼
async function startMicInput() {
    // 請求麥克風權限
    micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
        },
        video: false
    });

    if (audioCtx.state === "suspended") {
        await audioCtx.resume();
    }

    micSource = audioCtx.createMediaStreamSource(micStream);
    
    // 麥克風串流連接到 Analyser，方便做畫布波形視覺化
    micSource.connect(userAnalyser);

    // 建立 ScriptProcessor 節點進行編碼 (緩衝區為 2048，在 16kHz 下約為 128ms 封包，極輕量且流暢)
    scriptNode = audioCtx.createScriptProcessor(2048, 1, 1);
    
    // 門檻式靜音抑制 (Client-side VAD) 變數，避免背景雜訊使 Gemini 誤判為持續說話
    let micIsSpeaking = false;
    let silenceTicks = 0;
    const SILENCE_HOLD_TICKS = 8;     // Hold time (8 * 128ms ≈ 1.02秒，防止字音空隙被截斷)

    scriptNode.onaudioprocess = (e) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        
        // 此處取得的 audio 資料已經由瀏覽器原生的抗混疊 Resampler 完美降頻至 16000Hz
        const inputData = e.inputBuffer.getChannelData(0);
        
        // 關鍵優化：當麥克風被手動靜音時，不發送真實錄音，而是發送全 0 靜音封包
        // 這能確保背後的 WebSocket 保持熱度 (Keep-Alive)，Gemini Live 記憶不中斷，且不會發生 30 秒閒置斷線 (1011)！
        if (isMuted) {
            const silentBuffer = new Int16Array(inputData.length); // 預設全為 0
            ws.send(silentBuffer.buffer);
            return;
        }
        
        // A. 計算該音訊區間的最大振幅
        let maxVal = 0;
        for (let i = 0; i < inputData.length; i++) {
            const abs = Math.abs(inputData[i]);
            if (abs > maxVal) maxVal = abs;
        }
        
        // 讀取動態滑桿或快取的靈敏度設定 (解決固定門檻導致的斷線或靜音衝突)
        let silenceThreshold = vadSlider ? parseFloat(vadSlider.value) : 0.012;
        
        // 動態門檻判定：Gemini 正在說話時調高門檻 (防止喇叭回授/回音打斷模型發言)
        const isGeminiSpeaking = audioCtx && audioCtx.currentTime < nextStartTime;
        if (isGeminiSpeaking) {
            silenceThreshold = Math.max(silenceThreshold * 1.5, 0.018);
        }
        
        // B. Client-side VAD 判定
        if (maxVal >= silenceThreshold) {
            micIsSpeaking = true;
            silenceTicks = 0;
        } else {
            if (micIsSpeaking) {
                silenceTicks++;
                if (silenceTicks > SILENCE_HOLD_TICKS) {
                    micIsSpeaking = false;
                }
            }
        }
        
        // C. 串流維持與 VAD 動態控制 (關鍵優化：靜音時改送「全零 PCM 靜音影格」以維持 WebSocket 熱度)
        // 這可以防止 Google 負載均衡器或 websockets 因連線閒置而拋出 keepalive ping timeout (1011) 斷線！
        if (micIsSpeaking) {
            // 發言狀態：傳送真實錄音 Float32 轉 Int16 PCM ArrayBuffer
            const pcmBuffer = float32ToInt16(inputData);
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(pcmBuffer);
            }
        } else {
            // 靜音狀態：傳送長度相同、全為 0 的靜音封包以溫熱連線，同時維持伺服器 VAD 判定
            const silentBuffer = new Int16Array(inputData.length); // 預設全為 0
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(silentBuffer.buffer);
            }
        }
    };

    micSource.connect(scriptNode);
    scriptNode.connect(audioCtx.destination); // 必須連接到 destination 才能觸發 onaudioprocess
}

function stopMicInput() {
    if (scriptNode) {
        scriptNode.disconnect();
        scriptNode = null;
    }
    if (micSource) {
        micSource.disconnect();
        micSource = null;
    }
    if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
    }
}

// 9. 視訊影像擷取 (相機/螢幕)
async function startVideoInput(mode) {
    if (mode === "none") {
        videoPreviewWrapper.style.display = "none";
        return;
    }

    videoPreviewWrapper.style.display = "block";
    addLogMessage(`正在啟用視訊串流... 模式: ${mode === "camera" ? "鏡頭" : "螢幕分享"}`, "info");

    try {
        if (mode === "camera") {
            videoStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 5 } },
                audio: false
            });
            // 鏡頭模式通常需要鏡像顯示
            localVideo.style.transform = "scaleX(-1)";
        } else if (mode === "screen") {
            videoStream = await navigator.mediaDevices.getDisplayMedia({
                video: { width: { ideal: 1024 }, height: { ideal: 768 }, frameRate: { ideal: 5 } },
                audio: false
            });
            localVideo.style.transform = "none";
        }

        localVideo.srcObject = videoStream;

        // 建立一個隱藏 Canvas 用於將視訊幀轉成 JPEG
        const hiddenCanvas = document.createElement("canvas");
        const hCtx = hiddenCanvas.getContext("2d");

        // 定時擷取：每秒 1 幀 (1 fps)
        videoInterval = setInterval(() => {
            if (!ws || ws.readyState !== WebSocket.OPEN) return;
            if (localVideo.videoWidth === 0 || localVideo.videoHeight === 0) return;

            // 限制圖片最大寬高，避免寬頻負荷過重
            const maxDim = 480;
            let w = localVideo.videoWidth;
            let h = localVideo.videoHeight;
            if (w > maxDim || h > maxDim) {
                if (w > h) {
                    h = Math.round((h * maxDim) / w);
                    w = maxDim;
                } else {
                    w = Math.round((w * maxDim) / h);
                    h = maxDim;
                }
            }

            hiddenCanvas.width = w;
            hiddenCanvas.height = h;
            
            // 繪製目前的視訊影格
            hCtx.drawImage(localVideo, 0, 0, w, h);
            
            // 轉為 Base64 JPEG
            const dataUrl = hiddenCanvas.toDataURL("image/jpeg", 0.6); // 品質 0.6
            const base64Data = dataUrl.split(",")[1];
            
            // 送出給後端
            ws.send(JSON.stringify({
                type: "video",
                data: base64Data
            }));

        }, 1000);

    } catch (e) {
        addLogMessage(`視訊載入失敗: ${e.message}`, "error");
        console.error(e);
        voiceModeSelect.value = "none";
        videoPreviewWrapper.style.display = "none";
    }
}

function stopVideoInput() {
    if (videoInterval) {
        clearInterval(videoInterval);
        videoInterval = null;
    }
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    localVideo.srcObject = null;
    videoPreviewWrapper.style.display = "none";
}

// 音訊緩衝區合併器相關變數 (用於解決 lag 與爆音問題)
let audioAccumulator = new Int16Array(0);
let audioFlushTimeout = null;

// 10. Gemini 語音即時播放控制 (24kHz PCM)
function playPCM24kHz(arrayBuffer) {
    if (!audioCtx) return;
    
    const incoming = new Int16Array(arrayBuffer);
    
    // 將新到的音訊二進位資料與快取合併
    const merged = new Int16Array(audioAccumulator.length + incoming.length);
    merged.set(audioAccumulator, 0);
    merged.set(incoming, audioAccumulator.length);
    audioAccumulator = merged;
    
    // 清除既有的定時播放器
    if (audioFlushTimeout) {
        clearTimeout(audioFlushTimeout);
    }
    
    // 如果快取大於等於 200ms (24kHz 採樣率下為 4800 個採樣)，或是偵測到短暫靜音，就送出播放
    if (audioAccumulator.length >= 4800) {
        flushAudioBuffer();
    } else {
        // 延遲 50ms 播放最後不足 200ms 的殘存音訊，避免講完話最後一句被截斷
        audioFlushTimeout = setTimeout(flushAudioBuffer, 50);
    }
}

function flushAudioBuffer() {
    if (audioAccumulator.length === 0) return;
    
    const samples = audioAccumulator;
    audioAccumulator = new Int16Array(0);
    
    // A. 將 Int16 轉為 Float32
    const float32Array = new Float32Array(samples.length);
    for (let i = 0; i < samples.length; i++) {
        float32Array[i] = samples[i] / 32768.0;
    }
    
    // B. 建立 24kHz 音訊緩衝區
    const audioBuffer = audioCtx.createBuffer(1, float32Array.length, 24000);
    audioBuffer.getChannelData(0).set(float32Array);
    
    // C. 建立播放節點並連接到 Gemini Analyser
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(geminiAnalyser);
    
    // D. 低延遲時間排程 (Scheduling)
    const currentTime = audioCtx.currentTime;
    const startTime = Math.max(currentTime, nextStartTime);
    source.start(startTime);
    
    // E. 追蹤播放節點 (打斷時可以 stop)
    activeSources.push(source);
    
    const durationMs = audioBuffer.duration * 1000;
    const playDelayMs = (startTime - currentTime) * 1000;
    setTimeout(() => {
        const idx = activeSources.indexOf(source);
        if (idx > -1) {
            activeSources.splice(idx, 1);
        }
    }, playDelayMs + durationMs + 200);
    
    nextStartTime = startTime + audioBuffer.duration;
}

// 11. 語音打斷機制處理 (Interruption)
function handleInterruption() {
    addLogMessage("[語音已打斷]", "interrupted");
    
    // 立即停止當前所有語音播放
    interruptPlayback();
}

function interruptPlayback() {
    // 清除定時器與合併快取
    if (audioFlushTimeout) {
        clearTimeout(audioFlushTimeout);
        audioFlushTimeout = null;
    }
    audioAccumulator = new Int16Array(0);

    activeSources.forEach(source => {
        try {
            source.stop();
        } catch (e) {
            // 可能已經播放完畢
        }
    });
    activeSources = [];
    nextStartTime = 0;
    
    // 如果打斷時，Gemini Bubble 仍在說話狀態，移除其 glowing 樣式並重置標記
    if (currentGeminiBubble) {
        currentGeminiBubble.classList.remove("speaking");
        currentGeminiBubble = null;
        currentGeminiText = "";
    }
}

// 12. 接收文字逐字稿處理
function handleTextResponse(text) {
    currentGeminiText += text;
    
    // A. 如果沒有當前氣泡，建立一個新的
    if (!currentGeminiBubble) {
        currentGeminiBubble = document.createElement("div");
        currentGeminiBubble.className = "message-bubble gemini speaking";
        
        const sender = document.createElement("div");
        sender.className = "msg-sender";
        sender.innerHTML = '<i class="fa-solid fa-robot"></i> Gemini';
        
        const content = document.createElement("div");
        content.className = "msg-content";
        content.innerText = currentGeminiText;
        
        currentGeminiBubble.appendChild(sender);
        currentGeminiBubble.appendChild(content);
        chatLog.appendChild(currentGeminiBubble);
    } 
    // B. 如果有，直接更新氣泡內文字
    else {
        const contentNode = currentGeminiBubble.querySelector(".msg-content");
        contentNode.innerText = currentGeminiText;
    }
    
    // 自動滾動到底部
    chatLog.scrollTop = chatLog.scrollHeight;
}

// 13. 手動文字發言氣泡
function addUserMessageBubble(text) {
    // 當使用者手動打字時，重設 Gemini 的逐字稿標記
    currentGeminiBubble = null;
    currentGeminiText = "";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble user";
    
    const sender = document.createElement("div");
    sender.className = "msg-sender";
    sender.innerHTML = '您 <i class="fa-solid fa-user"></i>';
    
    const content = document.createElement("div");
    content.className = "msg-content";
    content.innerText = text;
    
    bubble.appendChild(sender);
    bubble.appendChild(content);
    chatLog.appendChild(bubble);
    
    chatLog.scrollTop = chatLog.scrollHeight;
}

// 14. 輔助函數：音訊降頻 Downsample (Float32Array)
function downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
    if (inputSampleRate === outputSampleRate) {
        return buffer;
    }
    if (inputSampleRate < outputSampleRate) {
        throw new Error("輸入採樣率必須大於輸出採樣率才能降頻");
    }
    const sampleRateRatio = inputSampleRate / outputSampleRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    
    while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
        let accum = 0;
        let count = 0;
        
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        
        result[offsetResult] = count > 0 ? accum / count : 0;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

// 15. 輔助函數：Float32 轉 Int16 ArrayBuffer
function float32ToInt16(buffer) {
    const l = buffer.length;
    const buf = new Int16Array(l);
    for (let i = 0; i < l; i++) {
        let s = Math.max(-1, Math.min(1, buffer[i]));
        // 將 -1.0 到 1.0 的 float32 轉換成 -32768 到 32767 的 Int16 範圍
        buf[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return buf.buffer;
}

// 16. 判定 Gemini 是否正在說話 (根據音訊緩衝排程)
function isGeminiSpeaking() {
    return audioCtx && audioCtx.currentTime < nextStartTime;
}

// 17. 音訊波形 Canvas 繪製 (雙向動態霓虹波形)
function drawVisualizers() {
    requestAnimationFrame(drawVisualizers);
    
    // A. 繪製麥克風波形 (粉紅色)
    // 只有在連線成功且沒有靜音的情況下，才顯示動態波形。否則繪製靜態線條
    const micActive = ws && ws.readyState === WebSocket.OPEN && !isMuted;
    drawWaveform(userCanvas, micActive ? userAnalyser : null, "#f43f5e", "#ff85a2");

    // B. 繪製 Gemini 語音波形 (藍靛色)
    // 只有在 Gemini 真正發言時才顯示動態，否則顯示靜態線條，並且切換氣泡的 speaking 樣式
    const geminiSpeaking = isGeminiSpeaking();
    drawWaveform(geminiCanvas, geminiSpeaking ? geminiAnalyser : null, "#6366f1", "#a5b4fc");
    
    // 動態更新 Gemini 對話框發言外框發光樣式
    if (currentGeminiBubble) {
        if (geminiSpeaking) {
            currentGeminiBubble.classList.add("speaking");
        } else {
            currentGeminiBubble.classList.remove("speaking");
        }
    }
}

function drawWaveform(canvas, analyser, mainColor, glowColor) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    
    ctx.clearRect(0, 0, w, h);

    // 背景微弱漸層
    ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
    ctx.fillRect(0, 0, w, h);

    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    
    if (!analyser) {
        // 靜態微弱水平線 (未啟動時呈現科幻平靜感)
        ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
        ctx.beginPath();
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();
        return;
    }

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    // 霓虹發光特效
    ctx.strokeStyle = mainColor;
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = 12;

    ctx.beginPath();
    const sliceWidth = w / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
        // v 在 0.0 到 2.0 之間，1.0 代表平靜無聲
        const v = dataArray[i] / 128.0;
        // 計算 y 座標
        const y = (v * h) / 2;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
        x += sliceWidth;
    }

    // 確保線條畫到邊界
    ctx.lineTo(w, h / 2);
    ctx.stroke();
    
    // 重置陰影防止影響其他繪製
    ctx.shadowBlur = 0;
}

// 18. UI 狀態管理
function setUIState(state) {
    if (state === "disconnected") {
        statusDot.className = "status-dot disconnected";
        statusText.innerText = "尚未連線";
        
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
        muteMicBtn.disabled = true;
        
        textInput.disabled = true;
        sendTextBtn.disabled = true;
        
        apiKeyInput.disabled = false;
        voiceModeSelect.disabled = false;
        voiceSelect.disabled = false;
    } 
    else if (state === "connecting") {
        statusDot.className = "status-dot connecting";
        statusText.innerText = "連線中...";
        
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        muteMicBtn.disabled = true;
        
        textInput.disabled = true;
        sendTextBtn.disabled = true;
        
        apiKeyInput.disabled = true;
        voiceModeSelect.disabled = true;
        voiceSelect.disabled = true;
    } 
    else if (state === "connected") {
        statusDot.className = "status-dot connected";
        statusText.innerText = "連線成功";
        
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        muteMicBtn.disabled = false;
        
        textInput.disabled = false;
        sendTextBtn.disabled = false;
        
        apiKeyInput.disabled = true;
        voiceModeSelect.disabled = true;
        voiceSelect.disabled = true;
    }
}

// 19. 對話日誌與系統日誌輸出
function addLogMessage(message, type = "info") {
    const logItem = document.createElement("div");
    
    if (type === "error") {
        logItem.className = "log-message error";
        logItem.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <span>${message}</span>`;
    } else if (type === "interrupted") {
        logItem.className = "log-message interrupted";
        logItem.innerHTML = `<i class="fa-solid fa-comment-slash"></i> <span>${message}</span>`;
    } else {
        logItem.className = "system-message";
        logItem.innerHTML = `<i class="fa-solid fa-circle-info"></i> <span>${message}</span>`;
    }
    
    chatLog.appendChild(logItem);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// 20. 通訊計時器
function startTimer() {
    connStartTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsed = Date.now() - connStartTime;
        const totalSecs = Math.floor(elapsed / 1000);
        const mins = Math.floor(totalSecs / 60).toString().padStart(2, "0");
        const secs = (totalSecs % 60).toString().padStart(2, "0");
        connectionTimer.innerText = `${mins}:${secs}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    connectionTimer.innerText = "00:00";
}
