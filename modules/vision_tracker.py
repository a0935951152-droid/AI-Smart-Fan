import time
import threading
import numpy as np
import cv2
import board
import busio
import adafruit_mlx90640
from ultralytics import YOLO

class BgTrackerV1:
    def __init__(self, percentile=50.0, ema_alpha=0.03):
        self.percentile = float(percentile)
        self.ema_alpha = float(ema_alpha)
        self.bg_ema = None
    def update(self, temp2d: np.ndarray) -> float:
        bg = float(np.percentile(temp2d.astype(np.float32), self.percentile))
        if self.bg_ema is None: self.bg_ema = bg
        else: self.bg_ema = (1.0 - self.ema_alpha) * self.bg_ema + self.ema_alpha * bg
        return float(self.bg_ema)

class VisionTracker:
    def __init__(self, model_path, scale=12, flip_ud=True, flip_lr=True):
        self.scale = scale
        self.flip_ud = flip_ud
        self.flip_lr = flip_lr
        self.img_width = 32 * scale
        self.img_height = 24 * scale
        self.img_center_x = self.img_width // 2
        
        # 影像預處理常數
        self.human_lo, self.human_hi = 34.0, 38.0
        self.bg_darken = 0.25
        self.bg_tracker = BgTrackerV1()
        
        # 載入硬體與模型
        print("👀 [Vision] 正在初始化 I2C 與 MLX90640...")
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
        self.mlx = adafruit_mlx90640.MLX90640(i2c)
        self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ 
        
        print(f"👀 [Vision] 正在載入 YOLO 模型 ({model_path})...")
        self.model = YOLO(model_path)
        
        # 🌟 執行緒共享變數 (主程式讀取用)
        self.lock = threading.Lock()
        self.person_count = 0
        self.target_error_x = 0     # 追蹤目標與中心的偏差
        self.latest_frame = None    # 用於 Flask 網頁串流的影像
        
        self.sweep_target = "left"  # 多人模式的掃描狀態
        self.is_running = True
        
        # 啟動背景視覺迴圈
        self.thread = threading.Thread(target=self._vision_loop, daemon=True)
        self.thread.start()
        print("✅ [Vision] 視覺追蹤模組已在背景啟動！")

    def _temp_to_gray(self, temp2d: np.ndarray, bg: float) -> np.ndarray:
        lo, hi = bg - 6.0, bg + 18.0
        x = np.clip((temp2d - lo) / (hi - lo), 0.0, 1.0)
        gray = (x * 255.0).astype(np.uint8)
        if self.bg_darken < 1.0:
            gray = (gray.astype(np.float32) * (1.0 - self.bg_darken)).astype(np.uint8)
        band = ((temp2d >= self.human_lo) & (temp2d <= self.human_hi)).astype(np.uint8) * 255
        center, half = (self.human_lo + self.human_hi) * 0.5, max(0.1, (self.human_hi - self.human_lo) * 0.5)
        boost = np.clip(1.0 - np.abs(temp2d - center) / half, 0.0, 1.0)
        g2 = gray.astype(np.int16)
        g2 += ((boost * 140.0).astype(np.int16) * (band > 0))
        g2 = np.clip(g2, 0, 255).astype(np.uint8)
        k = np.ones((3, 3), np.uint8)
        band2 = cv2.morphologyEx(band, cv2.MORPH_CLOSE, k, iterations=1)
        band2 = cv2.morphologyEx(band2, cv2.MORPH_OPEN, k, iterations=1)
        g2[cv2.Canny(band2, 60, 120) > 0] = 255
        return g2

    def _vision_loop(self):
        frame_data = np.zeros((24*32,))
        while self.is_running:
            try:
                self.mlx.getFrame(frame_data)
            except (ValueError, RuntimeError):
                continue
            
            # 1. 影像生成與翻轉
            temp = np.reshape(frame_data, (24, 32))
            if self.flip_ud: temp = np.flipud(temp)
            if self.flip_lr: temp = np.fliplr(temp)
            
            bg = self.bg_tracker.update(temp)
            gray24 = self._temp_to_gray(temp, bg)
            gray = cv2.resize(gray24, (self.img_width, self.img_height), interpolation=cv2.INTER_CUBIC)
            vis_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            # 2. YOLO 推論
            results = self.model.predict(source=vis_img, conf=0.70, verbose=False)
            boxes = results[0].boxes
            p_count = len(boxes)
            err_x = 0

            # 3. 畫框與邏輯計算
            if p_count > 0:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    cv2.rectangle(vis_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                if p_count == 1:
                    target_cx = (boxes[0].xyxy[0][0] + boxes[0].xyxy[0][2]) // 2
                    err_x = target_cx - self.img_center_x
                else:
                    sorted_boxes = sorted(boxes, key=lambda b: (b.xyxy[0][0] + b.xyxy[0][2]) / 2)
                    left_cx = (sorted_boxes[0].xyxy[0][0] + sorted_boxes[0].xyxy[0][2]) // 2
                    right_cx = (sorted_boxes[-1].xyxy[0][0] + sorted_boxes[-1].xyxy[0][2]) // 2

                    if self.sweep_target == "left":
                        target_cx = left_cx
                        if (target_cx - self.img_center_x) > -40: self.sweep_target = "right"
                    else:
                        target_cx = right_cx
                        if (target_cx - self.img_center_x) < 40: self.sweep_target = "left"
                    err_x = target_cx - self.img_center_x

            # 4. 更新執行緒安全變數
            with self.lock:
                self.person_count = p_count
                self.target_error_x = int(err_x)
                self.latest_frame = vis_img

    def get_tracking_data(self):
        """主程式呼叫此函式，瞬間取得最新的追蹤狀態與畫面"""
        with self.lock:
            return self.person_count, self.target_error_x, self.latest_frame

    def cleanup(self):
        self.is_running = False