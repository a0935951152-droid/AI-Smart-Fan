import time
import threading
import cv2
import numpy as np
import os
import sys
import tty
import termios

from flask import Flask, Response

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

from modules.fan_ctrl import FanController
from modules.motor_ctrl import MotorController
from modules.ir_receiver import IRReceiver
from modules.vision_tracker import VisionTracker
from modules.voice_brain import VoiceBrain
from modules.microphone_ctrl import MicrophoneController

# =========================
# 🌟 全域系統狀態變數
# =========================
sys_power = True        
sys_tracking = False     
sys_oscillating = False # 🌟 新增：是否正在自動擺頭
oscillate_dir = 1       # 🌟 新增：擺頭方向 (1為右，-1為左)
sys_status_text = "System Booting..." 

print("==================================================")
print("🚀 [系統] 正在啟動各大核心模組，請稍候...")
print("==================================================")

fan = FanController(pin_ina=24, pin_inb=25)
motor = MotorController(max_angle=60)
ir = IRReceiver()
vision = VisionTracker(model_path="weights/yolo/best.pt")
mic = MicrophoneController(card=2, device=0) 
brain = VoiceBrain(whisper_model="tiny", gguf_path="weights/qwen/qwen2.5-0.5b-instruct-q8_0.gguf") 

print("\n✅ [系統] 所有模組載入完畢！")

# =========================
# 2. 背景控制迴圈
# =========================
def hardware_control_loop():
    global sys_power, sys_tracking, sys_oscillating, oscillate_dir, sys_status_text
    import sys # 🌟 匯入 sys 模組來控制終端機輸出
    
    DEAD_ZONE = 50   
    TURN_DEG = 8     
    last_frame_id = None 

    # 🌟 新增一個小幫手函數：印出紅外線訊息後，重新補上打字提示
    def print_ir_event(msg):
        sys.stdout.write(f"\r\033[K{msg}\n")
        sys.stdout.write("👉 按下鍵盤 'e' 立刻開始錄音 4 秒 (按 'q' 離開): ") # 🌟 修改這行
        sys.stdout.flush()
    
    while True:
        # 1. 檢查紅外線指令
        ir_cmd = ir.get_command()
        if ir_cmd:
            if ir_cmd == "TOGGLE_TRACK":
                sys_tracking = not sys_tracking
                if sys_tracking:
                    sys_power = True
                    sys_oscillating = False 
                sys_status_text = f"Track Mode: {'ON' if sys_tracking else 'OFF'}"
                print_ir_event(f"📡 [IR] 遙控器切換追蹤模式 -> {sys_tracking}") # 🌟 替換原來的 print
                
            elif ir_cmd == "FAN_ON":
                sys_power = True
                fan.turn_on(speed=30) 
                sys_status_text = "IR: Fan ON"
                print_ir_event("📡 [IR] 遙控器開啟風扇 (30%)") # 🌟 替換
                
            elif ir_cmd == "FAN_OFF":
                fan.turn_off()
                sys_oscillating = False 
                sys_tracking = False
                sys_status_text = "IR: Fan OFF"
                print_ir_event("📡 [IR] 遙控器關閉風扇") # 🌟 替換
                
            elif ir_cmd == "SPEED_20":
                sys_power = True
                fan.turn_on(speed=20)
                sys_status_text = "IR: Speed 20%"
                print_ir_event("📡 [IR] 切換風速 20%") # 🌟 替換
                
            elif ir_cmd == "SPEED_50":
                sys_power = True
                fan.turn_on(speed=50)
                sys_status_text = "IR: Speed 50%"
                print_ir_event("📡 [IR] 切換風速 50%") # 🌟 替換
                
            elif ir_cmd == "SPEED_70":
                sys_power = True
                fan.turn_on(speed=70)
                sys_status_text = "IR: Speed 70%"
                print_ir_event("📡 [IR] 切換風速 70%") # 🌟 替換
                
            elif ir_cmd == "SPEED_100":
                sys_power = True
                fan.turn_on(speed=100)
                sys_status_text = "IR: Speed 100%"
                print_ir_event("📡 [IR] 切換風速 100%") # 🌟 替換
                
            elif ir_cmd == "OSCILLATE_ON" and sys_power:
                sys_oscillating = True
                sys_tracking = False 
                sys_status_text = "IR: Auto Oscillate ON"
                print_ir_event("📡 [IR] 開始自動擺頭") # 🌟 替換
            elif ir_cmd == "OSCILLATE_OFF" and sys_power:
                sys_oscillating = False
                sys_status_text = "IR: Auto Oscillate OFF"
                print_ir_event("📡 [IR] 停止自動擺頭") # 🌟 替換

        # 2. 處理自動擺頭邏輯
        if sys_power and sys_oscillating:
            # 碰到極限就反轉方向
            if motor.current_angle >= 50:
                oscillate_dir = -1
            elif motor.current_angle <= -50:
                oscillate_dir = 1
                
            # 慢慢轉動
            motor.rotate(turn_right=(oscillate_dir == 1), degrees=3)
            sys_status_text = "Auto Oscillating..."
            time.sleep(0.02) # 擺頭專用微小延遲，讓動作更滑順

        # 3. 處理 YOLO 自動追蹤 (擺頭關閉時才執行)
        elif sys_power and sys_tracking:
            p_count, err_x, frame = vision.get_tracking_data()
            if frame is not None and id(frame) != last_frame_id:
                last_frame_id = id(frame) 
                if p_count > 0:
                    if err_x > DEAD_ZONE: motor.rotate(turn_right=True, degrees=TURN_DEG)
                    elif err_x < -DEAD_ZONE: motor.rotate(turn_right=False, degrees=TURN_DEG)
                    else: sys_status_text = "Target Locked"
                else: sys_status_text = "Searching Target..."
                
        time.sleep(0.05)

# =========================
# 3. Flask 網頁串流設定
# =========================
app = Flask(__name__)

def generate_frames():
    HEADER_HEIGHT = 65
    while True:
        p_count, err_x, frame = vision.get_tracking_data()
        if frame is None:
            time.sleep(0.1)
            continue
            
        img_h, img_w = frame.shape[:2]
        canvas = np.zeros((img_h + HEADER_HEIGHT, img_w, 3), dtype=np.uint8)
        canvas[HEADER_HEIGHT:, :] = frame
        
        power_str = "ON" if sys_power else "OFF"
        track_str = "ON" if sys_tracking else "OFF"
        osc_str = "ON" if sys_oscillating else "OFF" # 新增擺頭狀態
        
        cv2.putText(canvas, f"PWR:{power_str} | TRK:{track_str} | OSC:{osc_str} | Ang:{motor.current_angle}", 
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        status_color = (0, 0, 255) if not sys_power else (0, 255, 0) if sys_tracking else (255, 0, 255) if sys_oscillating else (0, 255, 255)
        cv2.putText(canvas, f"Status: {sys_status_text}", 
                    (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 1, cv2.LINE_AA)
        
        ret, buffer = cv2.imencode('.jpg', canvas)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return '''
    <html><head><title>全端 AI 智慧風扇中樞</title></head>
    <body style="background-color:#222; color:white; text-align:center; font-family: sans-serif;">
        <h2>智慧風扇視覺監控面板</h2>
        <img src="/video_feed" style="border: 2px solid #555; border-radius: 8px;">
    </body></html>
    '''
@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 🌟 新增：讀取單一按鍵的底層函數 (免按 Enter)
def get_single_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        # setcbreak 模式：攔截單一按鍵，但保留 Ctrl+C 的中斷功能
        tty.setcbreak(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# =========================
# 4. 主執行緒：語音與大腦互動
# =========================
if __name__ == '__main__':
    threading.Thread(target=hardware_control_loop, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, use_reloader=False), daemon=True).start()
    
    print("\n==================================================")
    print("🚀 主控台已就緒！請開啟瀏覽器觀看畫面: http://localhost:5000")
    print("==================================================")
    
    try:
        while True:
            # 更新提示文字，加入 m 鍵的說明
            sys.stdout.write("\n👉 按 'e' 錄音 | 按 'm' 讀取音檔 | 按 'q' 離開: ")
            sys.stdout.flush()
            
            # 程式會停在這裡等待你的「單鍵觸發」
            key = get_single_key().lower()
            
            # 拿取當下的硬體狀態 (給大腦判斷用)
            current_ang = motor.current_angle
            p_count, err_x, _ = vision.get_tracking_data()

            if key == 'q':
                print("q") # 印出按下的鍵
                break
                
            elif key == 'e':
                print("e") 
                audio_file = mic.record(duration=4)
                if not audio_file: continue
                decision = brain.process_audio(audio_file, current_ang, p_count, err_x)
                
            elif key == 'm':
                print("m")
                # 按下 m 之後，恢復正常的輸入模式，讓你打字輸入檔名
                audio_file = input("🎵 請輸入音檔名 (例如 test_audio.mp3): ").strip()
                if not audio_file: 
                    continue
                decision = brain.process_audio(audio_file, current_ang, p_count, err_x)
                
            else:
                # 忽略按錯的其他按鍵
                continue
                
            print(f"⚡ [總管] 收到大腦決策: {decision}")

            # ======= 以下執行動作邏輯保持不變 =======
            if decision == "POWER_ON":
                sys_power = True
                sys_status_text = "Voice: Power ON"
                fan.turn_on(speed=30) 

            elif decision == "POWER_OFF":
                sys_power = False
                sys_tracking = False
                sys_oscillating = False
                sys_status_text = "Voice: Power OFF"
                motor.release() 
                fan.turn_off() 

            elif decision == "TRACK_ON":
                sys_power = True 
                sys_tracking = True
                sys_oscillating = False 
                sys_status_text = "Voice: Tracking ON"
                
            elif decision == "TRACK_OFF":
                sys_tracking = False
                sys_status_text = "Voice: Tracking OFF"
                
            elif decision == "AVOID" and sys_power:
                sys_tracking = False
                sys_oscillating = False
                sys_status_text = "Voice: Smart Avoiding"
                if err_x > 0: motor.rotate(turn_right=False, degrees=60)
                else: motor.rotate(turn_right=True, degrees=60)

            # 🌟 新增：回到正中央的動作
            elif decision == "CENTER" and sys_power:
                sys_tracking = False
                sys_oscillating = False
                sys_status_text = "Voice: Center"
                print("\n🏃‍♂️ [總管] 收到回正指令，馬達歸零中...")
                motor.center() # 呼叫馬達控制器的歸零函數

            elif decision == "TURN_LEFT" and sys_power:
                sys_tracking = False
                sys_oscillating = True
                sys_status_text = "Voice: Auto Oscillate ON"
                
            elif decision == "TURN_RIGHT" and sys_power:
                sys_tracking = False
                sys_oscillating = False
                sys_status_text = "Voice: Auto Oscillate OFF"
                
    except KeyboardInterrupt:
        print("\n🛑 收到終止訊號...")
    finally:
        if 'fan' in locals(): fan.cleanup()
        ir.cleanup()
        vision.cleanup()
        motor.cleanup()
        if 'brain' in locals():
            del brain 
        print("✅ 系統已安全關閉。")