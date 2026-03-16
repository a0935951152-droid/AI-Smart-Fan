import subprocess
import time
import os

class MicrophoneController:
    def __init__(self, card=1, device=0):
        """
        初始化麥克風控制器
        :param card: arecord -l 看到的 card 號碼 (通常 USB 麥克風是 1)
        :param device: arecord -l 看到的 device 號碼 (通常是 0)
        """
        self.card = card
        self.device = device
        self.output_path = "assets/live_command.wav"
        
        # 確保 assets 資料夾存在
        os.makedirs("assets", exist_ok=True)

    def record(self, duration=4):
        """錄製指定秒數的音檔"""
        print(f"\n🎙️ [Mic] 開始錄音 {duration} 秒... 請下達語音指令！")
        
        # 使用 plughw 可以讓系統自動處理硬體不支援的取樣率轉換
        hw_device = f"plughw:{self.card},{self.device}"
        
        # arecord 底層指令設定：S16_LE(16位元), 16000(16kHz), 1(單聲道)
        cmd = [
            "arecord",
            "-D", hw_device,
            "-f", "S16_LE",
            "-r", "16000",
            "-c", "1",
            "-d", str(duration),
            "-q",  # 安靜模式，隱藏底層警告訊息
            self.output_path
        ]
        
        try:
            # 阻塞程式，等待錄音完畢
            subprocess.run(cmd, check=True)
            print("✅ [Mic] 錄音結束，大腦準備接收！")
            return self.output_path
        except subprocess.CalledProcessError as e:
            print(f"❌ [Mic] 錄音失敗！請檢查麥克風是否插妥，或卡號是否正確: {e}")
            return None
        except FileNotFoundError:
            print("❌ [Mic] 系統缺少 alsa-utils，請執行 sudo apt-get install alsa-utils")
            return None