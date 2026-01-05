"""
视频生成模块
将音乐MP3 + 封面图片 + 歌词 合成为MP4视频，供VRChat USharpVideo使用
"""
import os
import re
import requests
import tempfile
import subprocess
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

class VideoGenerator:
    """视频生成器"""
    
    @staticmethod
    def parse_lrc(lrc_text):
        """
        解析LRC格式歌词
        返回: [(time_seconds, text), ...]
        """
        lyrics = []
        for line in lrc_text.split('\n'):
            match = re.search(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)', line)
            if match:
                m, s, ms_str, text = match.groups()
                text = text.strip()
                if not text:
                    continue
                ms = int(ms_str.ljust(3, '0')[:3])
                total_seconds = int(m) * 60 + int(s) + ms / 1000.0
                lyrics.append((total_seconds, text))
        return lyrics
    
    @staticmethod
    def generate_lyrics_srt(lyrics, translation_lyrics=None):
        """
        生成SRT字幕文件内容
        lyrics: [(time_seconds, text), ...]
        translation_lyrics: [(time_seconds, text), ...] 或 None
        """
        srt_content = []
        
        # 创建翻译映射
        trans_map = {}
        if translation_lyrics:
            for t, text in translation_lyrics:
                trans_map[t] = text
        
        for i, (time_sec, text) in enumerate(lyrics):
            # 计算结束时间（下一行的开始时间，或者当前+5秒）
            if i + 1 < len(lyrics):
                end_time_sec = lyrics[i + 1][0]
            else:
                end_time_sec = time_sec + 5.0
            
            # 转换为SRT时间格式
            start_time = VideoGenerator._seconds_to_srt_time(time_sec)
            end_time = VideoGenerator._seconds_to_srt_time(end_time_sec)
            
            # 查找翻译（容差±1秒）
            translation = None
            for t_time, t_text in trans_map.items():
                if abs(time_sec - t_time) < 1.0:
                    translation = t_text
                    break
            
            # 组合原文和翻译
            full_text = text
            if translation:
                full_text += f"\n{translation}"
            
            srt_content.append(f"{i+1}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(full_text)
            srt_content.append("")
        
        return "\n".join(srt_content)
    
    @staticmethod
    def _seconds_to_srt_time(seconds):
        """将秒数转换为SRT时间格式 HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    @staticmethod
    def create_lyric_image(lyrics, width=960, height=1080, font_size=40):
        """
        创建歌词图片（右侧显示）
        lyrics: [(time_seconds, text), ...]
        返回图片路径
        """
        img = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(img)
        
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", font_size)
            except:
                font = ImageFont.load_default()
        
        y_offset = 50
        for _, text in lyrics[:20]:  # 只显示前20行预览
            draw.text((50, y_offset), text, fill='white', font=font)
            y_offset += font_size + 20
            if y_offset > height - 100:
                break
        
        # 保存到临时文件
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_img.name)
        return temp_img.name
    
    @staticmethod
    def generate_video(audio_url, cover_url, lyrics_lrc, translation_lrc=None, song_name="未知歌曲", artist="未知歌手"):
        """
        生成MP4视频
        
        参数:
            audio_url: MP3音频链接
            cover_url: 封面图片链接
            lyrics_lrc: LRC格式歌词文本
            translation_lrc: LRC格式翻译歌词文本（可选）
            song_name: 歌曲名
            artist: 歌手名
            
        返回:
            生成的MP4文件路径
        """
        print(f"🎬 开始生成视频: {song_name} - {artist}")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. 下载音频
            print("📥 下载音频...")
            audio_path = os.path.join(temp_dir, "audio.mp3")
            audio_response = requests.get(audio_url, timeout=30)
            with open(audio_path, 'wb') as f:
                f.write(audio_response.content)
            
            # 2. 下载封面
            print("📥 下载封面...")
            cover_path = os.path.join(temp_dir, "cover.jpg")
            cover_response = requests.get(cover_url, timeout=30)
            with open(cover_path, 'wb') as f:
                f.write(cover_response.content)
            
            # 3. 调整封面大小为正方形1080x1080
            print("🖼️ 处理封面...")
            img = Image.open(cover_path)
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
            cover_resized = os.path.join(temp_dir, "cover_resized.jpg")
            img.save(cover_resized, quality=95)
            
            # 4. 解析歌词
            print("📝 解析歌词...")
            lyrics_parsed = VideoGenerator.parse_lrc(lyrics_lrc)
            translation_parsed = None
            if translation_lrc:
                translation_parsed = VideoGenerator.parse_lrc(translation_lrc)
            
            # 5. 生成SRT字幕
            srt_content = VideoGenerator.generate_lyrics_srt(lyrics_parsed, translation_parsed)
            srt_path = os.path.join(temp_dir, "lyrics.srt")
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            # 6. 使用FFmpeg合成视频
            print("🎥 合成视频...")
            output_path = os.path.join(temp_dir, "output.mp4")
            
            # FFmpeg命令：
            # - 左侧1080x1080封面
            # - 右侧960x1080黑色背景 + 字幕
            # - 总分辨率2040x1080
            
            # 简化方案：直接用封面作为视频背景 + 字幕叠加
            ffmpeg_cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', cover_resized,       # 封面图片
                '-i', audio_path,          # 音频
                '-vf', f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,subtitles={srt_path}:force_style='FontName=PingFang SC,FontSize=32,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Shadow=1,MarginV=50,Alignment=2'",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',               # 以音频长度为准
                '-y',                      # 覆盖输出文件
                output_path
            ]
            
            print(f"🔧 执行FFmpeg命令...")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ FFmpeg错误: {result.stderr}")
                raise Exception(f"FFmpeg执行失败: {result.stderr}")
            
            print(f"✅ 视频生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 视频生成失败: {e}")
            raise e
    
    @staticmethod
    def generate_video_simple(audio_url, cover_url, duration_seconds=None):
        """
        简化版视频生成（无字幕）
        快速生成一个封面+音频的MP4视频
        """
        print(f"🎬 开始生成简单视频")
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 下载音频
            audio_path = os.path.join(temp_dir, "audio.mp3")
            audio_response = requests.get(audio_url, timeout=30)
            with open(audio_path, 'wb') as f:
                f.write(audio_response.content)
            
            # 下载封面
            cover_path = os.path.join(temp_dir, "cover.jpg")
            cover_response = requests.get(cover_url, timeout=30)
            with open(cover_path, 'wb') as f:
                f.write(cover_response.content)
            
            # 调整封面
            img = Image.open(cover_path)
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            cover_resized = os.path.join(temp_dir, "cover_resized.jpg")
            img.save(cover_resized, quality=95)
            
            # 生成视频
            output_path = os.path.join(temp_dir, "output.mp4")
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', cover_resized,
                '-i', audio_path,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-tune', 'stillimage',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-pix_fmt', 'yuv420p',  # 确保兼容性
                '-y',
                output_path
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg执行失败: {result.stderr}")
            
            print(f"✅ 视频生成成功")
            return output_path
            
        except Exception as e:
            print(f"❌ 视频生成失败: {e}")
            raise e
