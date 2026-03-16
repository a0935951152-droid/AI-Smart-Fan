# 🌪️ Edge AI Smart Tracking Fan (全端 AI 智慧跟隨風扇)

這是一個基於 Raspberry Pi 執行的邊緣運算 (Edge AI) 智慧家庭專案。
系統整合了「視覺物件追蹤」、「離線大型語言模型 (LLM) 語音決策」、「紅外線遙控」以及「實體按鈕喚醒」功能，打造出一台完全不需依賴雲端、保護隱私且反應極速的次世代智慧風扇。

## 🌟 核心特色 (Features)
* **無頭模式 (Headless Demo Ready)**：支援實體按鈕 (GPIO) 喚醒，插電即用，不需螢幕鍵盤。
* **極速邊緣大腦**：使用 `llama.cpp` 驅動 Qwen2.5-0.5B 量化模型，語意決策推論時間 < 1 秒。
* **智慧視覺追蹤**：整合 YOLO 物件偵測與 MLX90640 熱成像，精準鎖定人體位置並控制步進馬達追蹤。
* **Web UI 即時監控**：內建 Flask 串流伺服器，可透過瀏覽器遠端監看追蹤畫面與系統狀態。
* **多重控制介面**：支援自然語音指令、實體按鈕、紅外線遙控器多軌並行控制。

---

## 🧩 系統模組架構 (Modules)

專案採用高度模組化的物件導向設計，各大核心模組皆可獨立測試與抽換：

* `main_supervisor.py`：**系統大總管**。負責啟動背景硬體迴圈、Flask 網頁伺服器、實體按鈕中斷 (GPIO 12)，並協調大腦與各硬體的動作。
* `modules/voice_brain.py`：**語音與決策大腦**。整合 `Faster-Whisper` 進行語音轉文字，並透過 `Llama(llama_cpp)` 進行語意理解與防呆攔截，輸出標準化控制指令。
* `modules/vision_tracker.py`：**視覺追蹤器**。負責讀取攝影機與 I2C 熱成像感測器，並透過 YOLO 模型計算人體與畫面中心的誤差值 (Error X)。
* `modules/motor_ctrl.py`：**頸部馬達控制器**。負責步進馬達的精準角度控制、極限防護，以及斷電定位與回正邏輯。
* `modules/fan_ctrl.py`：**風扇電源控制器**。負責透過 GPIO 控制風扇主馬達的啟閉與多段風速 (PWM)。
* `modules/ir_receiver.py`：**紅外線接收器**。嚴格的 NEC 協定解碼器，提供無延遲的遙控器控制體驗。
* `modules/microphone_ctrl.py`：**麥克風控制器**。負責精準錄製指定秒數的音訊檔供大腦分析。

---

## ⚙️ 重要參數設定 (Parameters)

若要微調系統手感，可修改以下核心參數：

### 1. 視覺與馬達 (Vision & Motor)
* `DEAD_ZONE = 50`：(於 main) 視覺追蹤的死區。目標在此像素範圍內時馬達不會作動，避免頻繁抖動。
* `TURN_DEG = 8`：(於 main) 追蹤模式下，馬達每次補償轉動的度數。
* `max_angle = 60`：(於 MotorController) 馬達左右轉動的安全極限角度 (正負 60 度)。

### 2. 語音大腦 (Voice Brain)
* `duration = 4`：(於 main) 實體按鈕按下後的錄音時間，預設 4 秒。
* `n_threads = 4`：(於 VoiceBrain) Llama.cpp 運算使用的 CPU 核心數，榨乾樹莓派效能。
* `n_ctx = 512`：(於 VoiceBrain) LLM 上下文長度限制，調低可大幅節省 RAM 佔用。

### 3. 硬體腳位 (GPIO BCM Mode)
* `BUTTON_PIN = 12`：實體喚醒按鈕，採用 `PUD_DOWN` 模式 (需接 3.3V)。
* `IR_PIN = 23`：紅外線接收器訊號腳位。

---

## 🚀 如何啟動 (How to Run)

1. 啟動虛擬環境：
   ```bash
   source ~/test/env/bin/activate

python main_supervisor.py
