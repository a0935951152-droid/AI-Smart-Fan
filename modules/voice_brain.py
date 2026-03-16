import time
import os
from faster_whisper import WhisperModel
# 🚀 拋棄 transformers，擁抱地表最強邊緣運算引擎
from llama_cpp import Llama

class VoiceBrain:
    def __init__(self, whisper_model="tiny", 
                 gguf_path="weights/qwen/qwen2.5-0.5b-instruct-q8_0.gguf"):
        print("==================================================")
        print(f"👂 [Voice] 正在載入耳朵 ({whisper_model})...")
        # Faster-Whisper 底層也是 CTranslate2 (C++)，我們保留它
        self.whisper = WhisperModel(whisper_model, device="cpu", compute_type="int8")
        
        print(f"🧠 [Brain] 正在載入 llama.cpp 量化大腦 ({os.path.basename(gguf_path)})...")
        try:
            # 🚀 啟動 Llama 引擎！
            # n_threads=4: 榨乾樹莓派的 4 顆核心
            # n_ctx=512: 限制上下文長度節省記憶體
            self.llm = Llama(
                model_path=gguf_path,
                n_threads=4,
                n_ctx=512,
                verbose=False # 關閉底層 C++ 的落落長日誌
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

        # 🌟 擴充錯字字典，並加入 CENTER (回正) 指令
        messages = [
            {"role": "system", "content": "你是風扇控制晶片。嚴禁廢話。只能輸出: POWER_ON, POWER_OFF, TRACK_ON, TRACK_OFF, AVOID, TURN_LEFT, TURN_RIGHT, OSCILLATE_ON, OSCILLATE_OFF, CENTER, IGNORE"},
            {"role": "user", "content": "【狀態】馬達:15度,人數:1,位置:畫面偏右【語音】轉到旁邊去"},
            {"role": "assistant", "content": "AVOID"},
            {"role": "user", "content": "【狀態】馬達:0度,人數:0,位置:沒看到人【語音】幫我開風扇"},
            {"role": "assistant", "content": "POWER_ON"},
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】開啟追蹤"},
            {"role": "assistant", "content": "TRACK_ON"},
            # 👇 針對 Whisper 的空耳錯字進行特訓
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】關閉風陣"},
            {"role": "assistant", "content": "POWER_OFF"},
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】開啟冒陷队"},
            {"role": "assistant", "content": "POWER_ON"},
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】崩散吹我"},
            {"role": "assistant", "content": "TRACK_ON"},
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】回到中央"},
            {"role": "assistant", "content": "CENTER"},
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】完畢"},
            {"role": "assistant", "content": "IGNORE"},
            {"role": "user", "content": "【狀態】馬達:60度,人數:0,位置:沒看到人【語音】1T,5,3"},
            {"role": "assistant", "content": "IGNORE"},
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
        
        # 🌟 終極攔截網：如果大腦還是發神經，我們直接掃描語音文字來補救！
        check_text = response + " " + text
        
        if "關閉追蹤" in check_text or "停指追蹤" in check_text: return "TRACK_OFF"
        elif "追蹤" in check_text or "跟著" in check_text or "吹我" in check_text: return "TRACK_ON"
        elif "關" in check_text or "停" in check_text: return "POWER_OFF"
        elif "開" in check_text: return "POWER_ON"
        elif "中央" in check_text or "回正" in check_text: return "CENTER"
        elif "擺頭" in check_text or "旋轉" in check_text: return "OSCILLATE_ON"
        elif "避" in check_text or "旁" in check_text: return "AVOID"
        elif "左" in check_text: return "TURN_LEFT"
        elif "右" in check_text: return "TURN_RIGHT"
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