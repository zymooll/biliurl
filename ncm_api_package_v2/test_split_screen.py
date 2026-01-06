#!/usr/bin/env python3
"""
测试左右分屏布局的视频生成功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ncm.core.video import VideoGenerator

def test_split_screen():
    """测试分屏布局"""
    
    # 使用网易云音乐API获取真实的音频和封面链接
    try:
        from ncm.core.music import get_song_info, get_song_url
        
        # 获取一首测试歌曲的信息（使用网易云音乐的热门歌曲）
        song_id = 1901371647  # 这是一个真实的歌曲ID
        
        print("🎵 获取歌曲信息...")
        song_info = get_song_info(song_id)
        audio_url = get_song_url(song_id, level="standard")
        
        if not audio_url:
            print("❌ 无法获取音频链接，使用模拟测试")
            return test_split_screen_mock()
            
        cover_url = song_info.get('al', {}).get('picUrl', '')
        song_name = song_info.get('name', '测试歌曲')
        artist = ', '.join([ar['name'] for ar in song_info.get('ar', [])])
        
        print(f"🎵 歌曲: {song_name} - {artist}")
        print(f"🖼️ 封面: {cover_url[:50]}...")
        print(f"🎧 音频: {audio_url[:50]}...")
        
    except Exception as e:
        print(f"❌ 获取歌曲信息失败: {e}，使用模拟测试")
        return test_split_screen_mock()
    
    # 简单的测试歌词
    lyrics_lrc = """[00:10.00]测试歌词第一句
[00:15.00]这是第二句歌词
[00:20.00]第三句歌词内容
[00:25.00]最后一句歌词
"""
    
    try:
        print("🧪 开始测试左右分屏布局...")
        
        video_path = VideoGenerator.generate_video(
            audio_url=audio_url,
            cover_url=cover_url,
            lyrics_lrc=lyrics_lrc,
            song_name=song_name,
            artist=artist,
            song_id="test_split_screen",
            level="test",
            use_gpu=False,  # 使用CPU编码以确保兼容性
            threads=2
        )
        
        print(f"✅ 测试成功！视频路径: {video_path}")
        
        # 检查文件大小
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            print(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
        
        return video_path
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None

def test_split_screen_mock():
    """使用模拟数据测试分屏布局"""
    
    # 创建测试用的音频和图片文件
    import tempfile
    from PIL import Image
    import subprocess
    
    temp_dir = tempfile.mkdtemp()
    
    # 创建测试封面图片
    test_cover = Image.new('RGB', (500, 500), color='blue')
    cover_path = os.path.join(temp_dir, "test_cover.jpg")
    test_cover.save(cover_path)
    
    # 创建测试音频（1秒的静音）
    audio_path = os.path.join(temp_dir, "test_audio.mp3")
    try:
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
            "-t", "30", "-c:a", "mp3", "-y", audio_path
        ], check=True, capture_output=True)
    except:
        print("❌ 无法创建测试音频文件，需要FFmpeg")
        return None
    
    # 使用文件路径作为URL
    audio_url = f"file://{audio_path}"
    cover_url = f"file://{cover_path}"
    
    lyrics_lrc = """[00:05.00]这是测试歌词第一句
[00:10.00]这是第二句歌词
[00:15.00]第三句歌词内容
[00:20.00]最后一句歌词
"""
    
    try:
        print("🧪 开始模拟测试左右分屏布局...")
        
        video_path = VideoGenerator.generate_video(
            audio_url=audio_url,
            cover_url=cover_url,
            lyrics_lrc=lyrics_lrc,
            song_name="模拟测试歌曲",
            artist="测试歌手",
            song_id="mock_test_split_screen",
            level="test",
            use_gpu=False,
            threads=2
        )
        
        print(f"✅ 模拟测试成功！视频路径: {video_path}")
        
        # 检查文件大小
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            print(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
        
        return video_path
        
    except Exception as e:
        print(f"❌ 模拟测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_split_screen()