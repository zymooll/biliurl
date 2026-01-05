import re

def process_lyrics_matching(yrc_text, tlyric_text):
    """
    将 YRC 逐字歌词与翻译歌词进行匹配
    返回格式: List[{time: int, duration: int, content: str, translation: str, json_content: object}]
    """
    try:
        # 1. 解析翻译歌词 (LRC 格式) -> {time_ms: translation_text}
        tlyric_map = {}
        for line in tlyric_text.split('\n'):
            # 匹配 [mm:ss.xx] 或 [mm:ss.xxx]
            match = re.search(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)', line)
            if match:
                m, s, ms_str = match.groups()[:3]
                text = match.group(4).strip()
                if not text: continue
                
                # 计算毫秒
                ms = int(ms_str.ljust(3, '0')[:3]) # 确保是3位
                total_ms = int(m) * 60000 + int(s) * 1000 + ms
                tlyric_map[total_ms] = text

        # 2. 解析 YRC 歌词
        result = []
        yrc_lines = yrc_text.split('\n')
        
        # 获取所有翻译的时间点并排序，用于查找最近的翻译
        t_times = sorted(tlyric_map.keys())
        
        for line in yrc_lines:
            # YRC 格式: [start, duration]...
            # 提取行开始时间
            match = re.search(r'^\[(\d+),(\d+)\]', line)
            if not match: continue
            
            start_time = int(match.group(1))
            duration = int(match.group(2))
            
            # 3. 查找匹配的翻译
            # 策略：在 YRC 开始时间附近寻找翻译 (容差 ±1000ms)
            # 优先找时间戳完全一致或非常接近的
            
            matched_trans = None
            min_diff = 1000 # 最大容差 1秒
            
            for t_time in t_times:
                diff = abs(start_time - t_time)
                if diff < min_diff:
                    min_diff = diff
                    matched_trans = tlyric_map[t_time]
                
                # 如果已经超过当前时间太多，后面的不用看了 (假设是有序的)
                if t_time > start_time + 1000:
                    break
            
            # 构造返回对象
            result.append({
                "time": start_time,
                "duration": duration,
                "raw": line, # 原始 YRC 行
                "translation": matched_trans # 匹配到的翻译
            })
            
        return result

    except Exception as e:
        print(f"❌ 歌词匹配处理出错: {e}")
        return []
