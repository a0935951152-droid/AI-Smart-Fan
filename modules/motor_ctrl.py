import RPi.GPIO as GPIO
import time
import threading

class MotorController:
    def __init__(self, in1=17, in2=18, in3=27, in4=22, 
                 max_angle=60, steps_per_rev=4096, reversed_motor=True):
        self.pins = [in1, in2, in3, in4]
        self.max_angle = max_angle
        self.steps_per_rev = steps_per_rev
        self.reversed_motor = reversed_motor
        self.current_angle = 0  
        
        # 🌟 執行緒安全鎖 (Thread Lock)：確保一次只有一個指令能控制馬達！
        self.lock = threading.Lock()
        
        self.step_sequence = [
            [1, 0, 0, 0], [1, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0],
            [0, 0, 1, 0], [0, 0, 1, 1], [0, 0, 0, 1], [1, 0, 0, 1]
        ]
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
        self.release()

    def set_step(self, w1, w2, w3, w4):
        for pin, val in zip(self.pins, [w1, w2, w3, w4]):
            GPIO.output(pin, val)

    def release(self):
        self.set_step(0, 0, 0, 0)

    def rotate(self, turn_right=True, degrees=5, speed=0.001):
        # 🌟 加上 with self.lock，霸佔馬達控制權，其他指令必須排隊
        with self.lock:
            if turn_right and self.current_angle + degrees > self.max_angle:
                degrees = self.max_angle - self.current_angle
            elif not turn_right and self.current_angle - degrees < -self.max_angle:
                degrees = self.current_angle - (-self.max_angle)
                
            if degrees <= 0:
                return 0  
                
            clockwise = not self.reversed_motor if turn_right else self.reversed_motor
            total_steps = int((self.steps_per_rev / 360) * degrees)
            seq = self.step_sequence if clockwise else list(reversed(self.step_sequence))
            
            for i in range(total_steps):
                self.set_step(*seq[i % 8])
                time.sleep(speed)
                
            self.release()
            self.current_angle += degrees if turn_right else -degrees
            return degrees

    def center(self):
        if self.current_angle > 0:
            self.rotate(turn_right=False, degrees=self.current_angle)
        elif self.current_angle < 0:
            self.rotate(turn_right=True, degrees=abs(self.current_angle))

    def cleanup(self):
        self.center()
        self.release()