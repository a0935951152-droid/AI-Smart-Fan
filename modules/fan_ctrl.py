import RPi.GPIO as GPIO

class FanController:
    def __init__(self, pin_ina=24, pin_inb=25):
        self.pin_ina = pin_ina
        self.pin_inb = pin_inb
        self.is_on = False
        self.current_speed = 0
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin_ina, GPIO.OUT)
        GPIO.setup(self.pin_inb, GPIO.OUT)
        
        # 🌟 初始化 PWM (頻率設為 1000Hz)
        self.pwm_a = GPIO.PWM(self.pin_ina, 1000)
        self.pwm_a.start(0) # 初始佔空比 0 (停止)
        GPIO.output(self.pin_inb, GPIO.LOW)

    def turn_on(self, speed=100):
        """開啟風扇 (預設 100% 全速，可傳入 0~100)"""
        self.current_speed = speed
        GPIO.output(self.pin_inb, GPIO.LOW)
        self.pwm_a.ChangeDutyCycle(speed) # 🌟 改變 PWM 佔空比來調速
        self.is_on = True
        print(f"💨 [Fan] 風扇已開啟 (轉速: {speed}%)")

    def set_speed(self, speed):
        """運轉中動態調整轉速 (0~100)"""
        if self.is_on:
            self.current_speed = speed
            self.pwm_a.ChangeDutyCycle(speed)
            print(f"💨 [Fan] 風扇轉速調整為: {speed}%")

    def turn_off(self):
        """關閉風扇"""
        self.pwm_a.ChangeDutyCycle(0)
        GPIO.output(self.pin_inb, GPIO.LOW)
        self.is_on = False
        self.current_speed = 0
        print("🛑 [Fan] 風扇已關閉。")

    def cleanup(self):
        self.turn_off()
        self.pwm_a.stop()