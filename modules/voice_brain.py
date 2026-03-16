import time
import os
from faster_whisper import WhisperModel
from llama_cpp import Llama

class VoiceBrain:
    def __init__(self, whisper_model="tiny", 
                 gguf_path="weights/qwen/qwen2.5-0.5b-instruct-q8_0.gguf"):
        print("==================================================")
        print(f"👂 [Voice] 正在載入耳朵 ({whisper_model})...")
        self.whisper = WhisperModel(whisper_model, device="cpu", compute_type="int8")
        
        print(f"🧠 [Brain] 正在載入 llama.cpp 量化大腦 ({os.path.basename(gguf_path)})...")
        try:
            self.llm = Llama(
                model_path=gguf_path,
                n_threads=4,
                n_ctx=512,
                verbose=False 
            )
            print("✅ [Brain] C++ 引擎驅動之語音與大腦系統載入完成！")
        except Exception as e:
            print(f"❌ [Brain] Llama.cpp 載入失敗: {e}")
            self.llm = None
        print("==================================================")

    def transcribe(self, audio_path):
        print(f"👂 [Voice] 正在聆聽 {audio_path}...")
        t0 = time.time()
        segments, _ = self.whisper.transcribe(audio_path, beam_size=5, language="zh")
        text = "".join([s.text for s in segments]).replace(" ", "")
        print(f"🗣️ [Voice] 辨識結果: 【{text}】 (耗時: {time.time()-t0:.2f}s)")
        return text

    def decide(self, text, current_angle, p_count, err_x):
        if not self.llm or not text: 
            return "IGNORE"
            
        target_pos = "正中央"
        if p_count == 0: target_pos = "沒看到人"
        elif err_x > 40: target_pos = "畫面偏右"
        elif err_x < -40: target_pos = "畫面偏左"

        user_content = f"【狀態】馬達:{current_angle}度,人數:{p_count},位置:{target_pos}【語音】{text}"

        # 🌟 1. 極簡化 Prompt：去除多餘字數，大幅減輕 Pi 3 閱讀負擔，提升推論速度
        messages = [
            {"role": "system", "content": "你是風扇晶片。僅輸出: POWER_ON, POWER_OFF, TRACK_ON, TRACK_OFF, AVOID, TURN_LEFT, TURN_RIGHT, OSCILLATE_ON, OSCILLATE_OFF, CENTER, IGNORE"},
            {"role": "user", "content": "【狀態】馬達:15度,人數:1,位置:畫面偏右【語音】轉到旁邊去"},
            {"role": "assistant", "content": "AVOID"},
            # 保留最核心的防呆範例
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】關閉風陣"},
            {"role": "assistant", "content": "POWER_OFF"},
            {"role": "user", "content": user_content} 
        ]
        
        print(f"🧠 [Brain] 思考中: {user_content}")
        t0 = time.time()
        
        result = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=5,      
            temperature=0.0,    
            stop=["\n", "<|im_end|>"] 
        )
        
        response = result["choices"][0]["message"]["content"].strip().upper()
        print(f"⏱️ [Brain] Llama.cpp 推論耗時 {time.time()-t0:.2f}s | 原始決策: {response}")
        
        # 🌟 2. 終極攔截網 2.0：優先比對「複合詞」，再比對「單字」，徹底解決誤殺問題
        check_text = response + " " + text
        
        # 第一層：最長/最明確的指令優先攔截
        if any(w in check_text for w in ["停止追蹤", "關閉追蹤", "取消追蹤", "停指追蹤", "追蹤停止", "停止最終"]): 
            return "TRACK_OFF"
        elif any(w in check_text for w in ["回到中央", "回正", "中間"]): 
            return "CENTER"
            
        # 第二層：動作單字攔截
        elif any(w in check_text for w in ["追蹤", "跟著", "吹我"]): 
            return "TRACK_ON"
        elif any(w in check_text for w in ["關", "停"]): 
            return "POWER_OFF"
        elif any(w in check_text for w in ["開", "啟動"]): 
            return "POWER_ON"
        elif any(w in check_text for w in ["擺頭", "旋轉"]): 
            return "OSCILLATE_ON"
        elif any(w in check_text for w in ["避", "旁"]): 
            return "AVOID"
        elif "左" in check_text: 
            return "TURN_LEFT"
        elif "右" in check_text: 
            return "TURN_RIGHT"
            
        # 第三層：信任大腦的合法輸出
        elif response in ["POWER_ON", "POWER_OFF", "TRACK_ON", "TRACK_OFF", "AVOID", "TURN_LEFT", "TURN_RIGHT", "OSCILLATE_ON", "OSCILLATE_OFF", "CENTER", "IGNORE"]:
            return response
            
        return "IGNORE"

    def process_audio(self, audio_path, current_angle, p_count, err_x):
        if not os.path.exists(audio_path) and os.path.exists(f"assets/{audio_path}"):
            audio_path = f"assets/{audio_path}"
        if not os.path.exists(audio_path):
            print(f"❌ [錯誤] 找不到音檔: {audio_path}")
            return "IGNORE"
            
        text = self.transcribe(audio_path)
        return self.decide(text, current_angle, p_count, err_x)