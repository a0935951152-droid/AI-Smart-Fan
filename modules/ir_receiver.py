import RPi.GPIO as GPIO
import time
import threading

class IRReceiver:
    def __init__(self, pin=23, 
                 code_oscillate_on='0xff10ef',   # 🌟 原向左鍵 -> 自動擺頭
                 code_oscillate_off='0xff5aa5',  # 🌟 原向右鍵 -> 停止擺頭
                 code_toggle_track='0xff629d',
                 code_fan_on='0xffa25d',
                 code_fan_off='0xffe21d',
                 code_speed_20='0xff22dd',       # 🌟 按鍵 1
                 code_speed_50='0xffc23d',       # 🌟 按鍵 2
                 code_speed_70='0xffe01f',       # 🌟 按鍵 3
                 code_speed_100='0xff906f'):     # 🌟 按鍵 4
        
        self.pin = pin
        self.code_oscillate_on = code_oscillate_on
        self.code_oscillate_off = code_oscillate_off
        self.code_toggle_track = code_toggle_track
        self.code_fan_on = code_fan_on
        self.code_fan_off = code_fan_off
        self.code_speed_20 = code_speed_20
        self.code_speed_50 = code_speed_50
        self.code_speed_70 = code_speed_70
        self.code_speed_100 = code_speed_100
        
        self.last_command = None
        self.is_running = True
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

    def _read_ir_code(self):
        while GPIO.input(self.pin) == GPIO.HIGH: pass
        times = []
        for _ in range(40): 
            t1 = time.perf_counter()
            while GPIO.input(self.pin) == GPIO.LOW:
                if time.perf_counter() - t1 > 0.05: break
            t2 = time.perf_counter()
            while GPIO.input(self.pin) == GPIO.HIGH:
                if time.perf_counter() - t2 > 0.05: break 
            times.append(time.perf_counter() - t2)
            
        bits = []
        for t in times:
            if 0.0010 < t < 0.0030:   bits.append(1)
            elif 0.0002 < t <= 0.0010: bits.append(0)
                
        if len(bits) >= 32:
            bits = bits[:32]
            code = 0
            for bit in bits:
                code = (code << 1) | bit
            return hex(code)
        return None

    def _listen_loop(self):
        while self.is_running:
            GPIO.wait_for_edge(self.pin, GPIO.FALLING)
            code = self._read_ir_code()
            
            if code:
                print(f"📡 [IR] 收到紅外線碼: {code}")
                # 🌟 全新對應邏輯
                if code == self.code_oscillate_on: self.last_command = "OSCILLATE_ON"
                elif code == self.code_oscillate_off: self.last_command = "OSCILLATE_OFF"
                elif code == self.code_toggle_track: self.last_command = "TOGGLE_TRACK"
                elif code == self.code_fan_on: self.last_command = "FAN_ON"
                elif code == self.code_fan_off: self.last_command = "FAN_OFF"
                elif code == self.code_speed_20: self.last_command = "SPEED_20"
                elif code == self.code_speed_50: self.last_command = "SPEED_50"
                elif code == self.code_speed_70: self.last_command = "SPEED_70"
                elif code == self.code_speed_100: self.last_command = "SPEED_100"
            
            time.sleep(0.3)

    def get_command(self):
        cmd = self.last_command
        self.last_command = None
        return cmd

    def cleanup(self):
        self.is_running = False