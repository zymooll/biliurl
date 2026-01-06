"""
视频生成模块
将音乐MP3 + 封面图片 + 歌词 合成为MP4视频，供VRChat USharpVideo使用
"""
import os
import shlex
import re
import sys
import hashlib
import shutil
import requests
import tempfile
import subprocess
import multiprocessing
import uuid
import threading
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

class VideoGenerator:
    """视频生成器"""
    
    # 缓存目录 - 使用项目目录下的持久化存储
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "video_cache")
    
    @staticmethod
    def _get_ffmpeg_path():
        """
        获取 FFmpeg 可执行文件路径
        Linux 上优先使用系统 FFmpeg（/usr/bin/ffmpeg），避免 Conda 环境的库冲突
        """
        if sys.platform.startswith("linux"):
            # 优先使用系统 FFmpeg，它包含完整的硬件加速支持
            if os.path.exists("/usr/bin/ffmpeg"):
                return "/usr/bin/ffmpeg"
        # 其他平台使用 PATH 中的 ffmpeg
        return "ffmpeg"
    
    @staticmethod
    def _ensure_cache_dir():
        """确保缓存目录存在"""
        if not os.path.exists(VideoGenerator.CACHE_DIR):
            os.makedirs(VideoGenerator.CACHE_DIR, exist_ok=True)
    
    @staticmethod
    def _get_cache_key(song_id, level, with_lyrics=True):
        """生成缓存key - 使用歌曲ID作为文件名"""
        lyrics_suffix = "lyrics" if with_lyrics else "simple"
        return f"{song_id}_{level}_{lyrics_suffix}"
    
    @staticmethod
    def _get_cached_video(song_id, level, with_lyrics=True):
        """获取缓存的视频（排除正在生成的.tmp文件）"""
        VideoGenerator._ensure_cache_dir()
        cache_key = VideoGenerator._get_cache_key(song_id, level, with_lyrics)
        cache_path = os.path.join(VideoGenerator.CACHE_DIR, f"{cache_key}.mp4")
        tmp_path = f"{cache_path}.tmp"
        
        # 如果临时文件存在，说明正在生成，不使用缓存
        if os.path.exists(tmp_path):
            print(f"⏳ 视频正在生成中: {cache_key}")
            return None
        
        if os.path.exists(cache_path):
            # 检查文件是否有效（至少1MB）
            file_size = os.path.getsize(cache_path)
            if file_size > 1024 * 1024:
                print(f"✅ 使用缓存视频: {cache_path} ({file_size / 1024 / 1024:.2f} MB)")
                return cache_path
            else:
                print(f"⚠️ 缓存文件异常（{file_size} bytes），将重新生成")
                try:
                    os.remove(cache_path)
                except:
                    pass
        return None
    
    @staticmethod
    def _save_to_cache(video_path, song_id, level, with_lyrics=True):
        """保存视频到持久化缓存"""
        try:
            VideoGenerator._ensure_cache_dir()
            cache_key = VideoGenerator._get_cache_key(song_id, level, with_lyrics)
            cache_path = os.path.join(VideoGenerator.CACHE_DIR, f"{cache_key}.mp4")
            
            # 如果源文件就在缓存目录，直接返回
            if os.path.abspath(video_path) == os.path.abspath(cache_path):
                print(f"💾 视频已在缓存目录: {cache_path}")
                return cache_path
            
            # 移动文件到缓存目录（而不是复制，节省空间）
            shutil.move(video_path, cache_path)
            print(f"💾 视频已持久化存储: {cache_path}")
            return cache_path
        except Exception as e:
            print(f"⚠️ 缓存保存失败: {e}")
            return video_path

    @staticmethod
    def _select_encoder(use_gpu=False, gpu_device: str | None = None):
        """选择编码器和附加参数，按需启用硬件加速"""
        if not use_gpu:
            return {
                "encoder": "libx264",
                "encoder_args": ['-preset', 'fast', '-crf', '23'],
                "vf_suffix": None,
                "pre_args": []
            }

        platform = sys.platform
        if platform == "darwin":
            return {
                "encoder": "h264_videotoolbox",
                "encoder_args": ['-b:v', '4M'],
                "vf_suffix": None,
                "pre_args": []
            }

        if platform.startswith("linux"):
            # Intel 核显：优先使用 VAAPI (Video Acceleration API)，兼容性更好
            device = gpu_device or "/dev/dri/renderD128"
            
            # 检查设备是否存在
            if not os.path.exists(device):
                print(f"⚠️ 设备 {device} 不存在，尝试查找其他设备...")
                # 尝试查找可用的设备
                for i in range(128, 132):
                    alt_device = f"/dev/dri/renderD{i}"
                    if os.path.exists(alt_device):
                        print(f"✅ 找到设备: {alt_device}")
                        device = alt_device
                        break
                else:
                    print("⚠️ 未找到可用的硬件设备，降级使用软件编码")
                    return {
                        "encoder": "libx264",
                        "encoder_args": ['-preset', 'fast', '-crf', '23'],
                        "vf_suffix": None,
                        "pre_args": []
                    }
            
            # 验证 VAAPI 是否真正可用（使用系统 ffmpeg 测试）
            try:
                # 使用系统 ffmpeg 测试 VAAPI 设备是否可用（避免 Conda 的库冲突）
                ffmpeg_path = VideoGenerator._get_ffmpeg_path()
                test_result = subprocess.run(
                    [ffmpeg_path, '-init_hw_device', f'vaapi=va:{device}', '-f', 'lavfi', '-i', 'nullsrc', '-t', '0.001', '-f', 'null', '-'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if test_result.returncode != 0 or 'No VA display found' in test_result.stderr or 'Device creation failed' in test_result.stderr:
                    print(f"⚠️ VAAPI 设备 {device} 不可用，降级使用软件编码")
                    print(f"   原因: {test_result.stderr[:200] if test_result.stderr else '未知错误'}")
                    return {
                        "encoder": "libx264",
                        "encoder_args": ['-preset', 'fast', '-crf', '23'],
                        "vf_suffix": None,
                        "pre_args": []
                    }
            except subprocess.TimeoutExpired:
                print("⚠️ VAAPI 检测超时，降级使用软件编码")
                return {
                    "encoder": "libx264",
                    "encoder_args": ['-preset', 'fast', '-crf', '23'],
                    "vf_suffix": None,
                    "pre_args": []
                }
            except Exception as e:
                print(f"⚠️ VAAPI 检测失败: {e}，降级使用软件编码")
                return {
                    "encoder": "libx264",
                    "encoder_args": ['-preset', 'fast', '-crf', '23'],
                    "vf_suffix": None,
                    "pre_args": []
                }
            
            # 使用 VAAPI（Video Acceleration API）硬件加速
            print(f"✅ 使用 VAAPI 硬件加速: {device}")
            return {
                "encoder": "h264_vaapi",
                "encoder_args": [
                    '-compression_level', '2',  # 压缩级别 (0-7)
                ],
                "vf_suffix": "format=nv12,hwupload=extra_hw_frames=64",
                "pre_args": [
                    '-init_hw_device', f'vaapi=va:{device}',
                    '-filter_hw_device', 'va'
                ]
            }

        if platform.startswith("win"):
            return {
                "encoder": "h264_nvenc",
                "encoder_args": ['-b:v', '4M'],
                "vf_suffix": None,
                "pre_args": []
            }

        return {
            "encoder": "libx264",
            "encoder_args": ['-preset', 'fast', '-crf', '23'],
            "vf_suffix": None,
            "pre_args": []
        }
    
    @staticmethod
    def parse_lrc(lrc_text):
        """
        解析LRC格式歌词
        支持多种时间戳格式：
        - [00:12.34] 标准格式
        - [00:12:34] 冒号分隔
        - [00:12.345] 3位毫秒
        返回: [(time_seconds, text), ...]
        """
        if not lrc_text:
            return []
        
        lyrics = []
        for line_num, line in enumerate(lrc_text.split('\n'), 1):
            # 尝试匹配标准格式 [mm:ss.xxx] 或 [mm:ss:xxx]
            match = re.search(r'\[(\d{2}):(\d{2})[\.:,](\d{2,3})\](.*)', line)
            if match:
                m, s, ms_str, text = match.groups()
                text = text.strip()
                if not text:
                    continue
                ms = int(ms_str.ljust(3, '0')[:3])
                total_seconds = int(m) * 60 + int(s) + ms / 1000.0
                lyrics.append((total_seconds, text))
            else:
                # 如果有时间戳但格式不匹配，输出调试信息
                if line.strip() and line.strip().startswith('[') and ']' in line:
                    if line_num <= 5:  # 只打印前5行示例
                        print(f"⚠️ 第{line_num}行歌词格式不匹配: {line[:50]}")
        
        if not lyrics:
            print("⚠️ 未能解析出任何有效歌词行")
        
        return lyrics
    
    @staticmethod
    def generate_lyrics_srt(lyrics, translation_lyrics=None):
        """
        生成SRT字幕文件内容
        lyrics: [(time_seconds, text), ...]
        translation_lyrics: [(time_seconds, text), ...] 或 None
        """
        if not lyrics or len(lyrics) == 0:
            return ""
        
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
    def generate_video(audio_url, cover_url, lyrics_lrc, translation_lrc=None, song_name="未知歌曲", artist="未知歌手", use_gpu=False, threads=None, gpu_device=None, song_id=None, level="standard"):
        """
        生成MP4视频
        
        参数:
            audio_url: MP3音频链接
            cover_url: 封面图片链接
            lyrics_lrc: LRC格式歌词文本
            translation_lrc: LRC格式翻译歌词文本（可选）
            song_name: 歌曲名
            artist: 歌手名
            song_id: 歌曲ID（用于缓存）
            level: 音质等级（用于缓存）
            
        返回:
            生成的MP4文件路径
        """
        print(f"🎬 开始生成视频: {song_name} - {artist} (ID: {song_id})")
        
        # 检查缓存
        if song_id:
            cached_video = VideoGenerator._get_cached_video(song_id, level, with_lyrics=True)
            if cached_video:
                return cached_video
        
        # 准备输出路径：使用 .tmp 后缀 + UUID，完成后重命名（原子操作）
        VideoGenerator._ensure_cache_dir()
        
        # 生成唯一标识符（线程安全）
        unique_id = uuid.uuid4().hex[:8]
        thread_id = threading.current_thread().ident
        
        if song_id:
            cache_key = VideoGenerator._get_cache_key(song_id, level, with_lyrics=True)
            final_path = os.path.join(VideoGenerator.CACHE_DIR, f"{cache_key}.mp4")
            # 使用 UUID 避免多线程冲突
            output_path = os.path.join(VideoGenerator.CACHE_DIR, f"{cache_key}_{unique_id}_{thread_id}.tmp")
            print(f"📝 缓存文件名: {cache_key}.mp4 (临时ID: {unique_id})")
        else:
            # 如果没有song_id，使用临时文件
            final_path = None
            temp_base = tempfile.mkdtemp(prefix=f"ncm_video_{unique_id}_")
            output_path = os.path.join(temp_base, "output.mp4")
        
        # 创建临时目录用于中间文件（使用唯一前缀）
        temp_dir = tempfile.mkdtemp(prefix=f"ncm_temp_{unique_id}_")
        
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
            # 如果是RGBA模式，转换为RGB（JPEG不支持透明度）
            if img.mode == 'RGBA':
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
            cover_resized = os.path.join(temp_dir, "cover_resized.jpg")
            img.save(cover_resized, quality=95)
            
            # 4. 解析歌词
            print("📝 解析歌词...")
            print(f"原始歌词长度: {len(lyrics_lrc) if lyrics_lrc else 0} 字符")
            lyrics_parsed = VideoGenerator.parse_lrc(lyrics_lrc)
            print(f"解析结果: {len(lyrics_parsed)} 行歌词")
            translation_parsed = None
            if translation_lrc:
                print(f"翻译歌词长度: {len(translation_lrc)} 字符")
                translation_parsed = VideoGenerator.parse_lrc(translation_lrc)
                print(f"翻译解析结果: {len(translation_parsed)} 行")
            
            # 5. 生成SRT字幕
            srt_content = VideoGenerator.generate_lyrics_srt(lyrics_parsed, translation_parsed)
            srt_path = os.path.join(temp_dir, "lyrics.srt")
            
            # 检查字幕内容
            if not srt_content or not srt_content.strip():
                print("⚠️ 字幕内容为空，使用简化模式")
                return VideoGenerator.generate_video_simple(audio_url, cover_url, use_gpu, threads, gpu_device)
            
            # 写入字幕文件
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            # 验证文件是否成功创建
            if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
                print("⚠️ 字幕文件创建失败，使用简化模式")
                return VideoGenerator.generate_video_simple(audio_url, cover_url, use_gpu, threads, gpu_device)
            
            print(f"✅ 字幕文件已生成: {srt_path} ({os.path.getsize(srt_path)} bytes)")
            
            # 6. 使用FFmpeg合成视频
            print("🎥 合成视频...")
            
            # FFmpeg命令：
            # - 左侧1080x1080封面
            # - 右侧960x1080黑色背景 + 字幕
            # - 总分辨率2040x1080
            
            # 简化方案：直接用封面作为视频背景 + 字幕叠加
            enc_conf = VideoGenerator._select_encoder(use_gpu, gpu_device)
            encoder = enc_conf["encoder"]
            
            # 优化线程数：如果未指定则使用CPU核心数（性能更好）
            if threads is None:
                threads = multiprocessing.cpu_count()
                print(f"🔢 自动检测到 {threads} 个CPU核心")
            thread_count = str(threads)

            video_codec_args = ['-c:v', encoder] + enc_conf["encoder_args"]

            # 构建视频滤镜链
            # 注意：subtitles 滤镜必须在 hwupload 之前（CPU端处理）
            # 使用最简单的方式：只指定字幕文件，不使用 force_style（避免复杂的转义问题）
            vf_chain = f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,subtitles={srt_path}"
            if enc_conf["vf_suffix"]:
                # VAAPI: 字幕渲染后再上传到GPU
                vf_chain = f"{vf_chain},{enc_conf['vf_suffix']}"
            
            print(f"🎨 使用编码器: {encoder}")
            print(f"🔧 滤镜链: {vf_chain[:100]}...")  # 只打印前100字符

            # 构建FFmpeg命令
            # 注意：QSV 和 VAAPI 不能使用 -pix_fmt yuv420p，会导致硬件加速失效
            pix_fmt_args = [] if encoder in ["h264_qsv", "h264_vaapi"] else ['-pix_fmt', 'yuv420p']
            
            ffmpeg_path = VideoGenerator._get_ffmpeg_path()
            ffmpeg_cmd = [
                ffmpeg_path,
                '-threads', thread_count,
            ] + enc_conf["pre_args"] + [
                '-loop', '1',
                '-i', cover_resized,
                '-i', audio_path,
                '-vf', vf_chain,
            ] + video_codec_args + [
                '-c:a', 'aac',
                '-b:a', '192k',
            ] + pix_fmt_args + [
                '-shortest',
                '-movflags', '+faststart',
                '-f', 'mp4',  # 明确指定输出格式为 mp4（支持 .tmp 扩展名）
                '-y',
                output_path
            ]
            
            print(f"🔧 执行FFmpeg命令: {' '.join(ffmpeg_cmd[:20])}...")
            
            # 清理 Conda 环境变量，避免库链接冲突
            env = os.environ.copy()
            removed_keys = []
            for key in list(env.keys()):
                if 'CONDA' in key or 'LD_PRELOAD' in key:
                    removed_keys.append(key)
                    del env[key]
            
            # 只在使用 VAAPI 硬件加速时设置环境变量
            if use_gpu and enc_conf["encoder"] == "h264_vaapi":
                env['LIBVA_DRIVER_NAME'] = 'iHD'
                env['LIBVA_DRM_DEVICE'] = gpu_device or '/dev/dri/renderD128'  # 使用检测到的设备
                env['LIBVA_DRIVERS_PATH'] = '/usr/lib/x86_64-linux-gnu/dri'
                print(f"🔧 已设置 VAAPI 环境: device={env['LIBVA_DRM_DEVICE']}")
            
            if removed_keys:
                print(f"🔧 已清理环境变量: {', '.join(removed_keys)}")
            
            # 直接传递列表，不使用 shell=True
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                print(f"❌ FFmpeg错误: {result.stderr}")
                raise Exception(f"FFmpeg执行失败: {result.stderr}")
            
            print(f"✅ 视频生成成功: {output_path}")
            
            # 原子性重命名：.tmp -> .mp4（确保并发安全）
            if song_id and final_path:
                try:
                    # 使用 os.replace 而不是 os.rename，更安全（即使目标文件存在也会原子替换）
                    # 但在重命名前先检查是否有其他线程已经完成了
                    if not os.path.exists(final_path):
                        os.replace(output_path, final_path)
                        print(f"💾 视频已持久化存储: {final_path}")
                        output_path = final_path
                    else:
                        # 其他线程已经生成完成，删除当前的临时文件
                        print(f"ℹ️ 其他线程已完成视频生成，使用已有文件")
                        try:
                            os.remove(output_path)
                        except:
                            pass
                        output_path = final_path
                except FileExistsError:
                    # 竞争条件：其他线程已创建文件
                    print(f"ℹ️ 检测到并发生成，使用已有文件")
                    try:
                        os.remove(output_path)
                    except:
                        pass
                    output_path = final_path
                except Exception as e:
                    print(f"⚠️ 重命名失败: {e}")
                    # 即使重命名失败，临时文件仍然可用
            
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            return output_path
            
        except Exception as e:
            print(f"❌ 视频生成失败: {e}")
            # 清理临时文件和.tmp文件
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            if song_id and os.path.exists(output_path):
                try:
                    os.remove(output_path)  # 删除未完成的.tmp文件
                    print(f"🗑️ 已清理未完成的临时文件")
                except:
                    pass
            raise e
    
    @staticmethod
    def generate_video_simple(audio_url, cover_url, duration_seconds=None, use_gpu=False, threads=None, gpu_device=None, song_id=None, level="standard"):
        """
        简化版视频生成（无字幕）
        快速生成一个封面+音频的MP4视频
        """
        print(f"🎬 开始生成简单视频 (ID: {song_id})")
        
        # 检查缓存
        if song_id:
            cached_video = VideoGenerator._get_cached_video(song_id, level, with_lyrics=False)
            if cached_video:
                return cached_video
        
        # 准备输出路径：使用 .tmp 后缀 + UUID，完成后重命名（原子操作）
        VideoGenerator._ensure_cache_dir()
        
        # 生成唯一标识符（线程安全）
        unique_id = uuid.uuid4().hex[:8]
        thread_id = threading.current_thread().ident
        
        if song_id:
            cache_key = VideoGenerator._get_cache_key(song_id, level, with_lyrics=False)
            final_path = os.path.join(VideoGenerator.CACHE_DIR, f"{cache_key}.mp4")
            # 使用 UUID 避免多线程冲突
            output_path = os.path.join(VideoGenerator.CACHE_DIR, f"{cache_key}_{unique_id}_{thread_id}.tmp")
            print(f"📝 缓存文件名: {cache_key}.mp4 (临时ID: {unique_id})")
        else:
            # 如果没有song_id，使用临时文件
            final_path = None
            temp_base = tempfile.mkdtemp(prefix=f"ncm_video_{unique_id}_")
            output_path = os.path.join(temp_base, "output.mp4")
        
        # 创建临时目录用于中间文件（使用唯一前缀）
        temp_dir = tempfile.mkdtemp(prefix=f"ncm_temp_{unique_id}_")
        
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
            # 如果是RGBA模式，转换为RGB（JPEG不支持透明度）
            if img.mode == 'RGBA':
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            cover_resized = os.path.join(temp_dir, "cover_resized.jpg")
            img.save(cover_resized, quality=95)
            
            # 生成视频（output_path 已在上面定义）
            enc_conf = VideoGenerator._select_encoder(use_gpu, gpu_device)
            encoder = enc_conf["encoder"]
            
            # 优化线程数：如果未指定则使用CPU核心数（性能更好）
            if threads is None:
                threads = multiprocessing.cpu_count()
                print(f"🔢 自动检测到 {threads} 个CPU核心")
            thread_count = str(threads)

            video_codec_args = ['-c:v', encoder] + enc_conf["encoder_args"]

            vf_chain = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
            if enc_conf["vf_suffix"]:
                vf_chain = f"{vf_chain},{enc_conf['vf_suffix']}"
            
            print(f"🎨 使用编码器: {encoder}")
            
            # QSV 和 VAAPI 不能使用 -pix_fmt yuv420p
            pix_fmt_args = [] if encoder in ["h264_qsv", "h264_vaapi"] else ['-pix_fmt', 'yuv420p']

            ffmpeg_path = VideoGenerator._get_ffmpeg_path()
            ffmpeg_cmd = [
                ffmpeg_path,
                '-threads', thread_count,
            ] + enc_conf["pre_args"] + [
                '-loop', '1',
                '-i', cover_resized,
                '-i', audio_path,
                '-vf', vf_chain,
            ] + video_codec_args + [
                '-c:a', 'aac',
                '-b:a', '192k',
            ] + pix_fmt_args + [
                '-shortest',
                '-movflags', '+faststart',
                '-f', 'mp4',  # 明确指定输出格式为 mp4（支持 .tmp 扩展名）
                '-y',
                output_path
            ]
            
            print(f"🔧 执行FFmpeg命令: {' '.join(ffmpeg_cmd[:15])}...")
            
            # 清理 Conda 环境变量，避免库链接冲突
            env = os.environ.copy()
            removed_keys = []
            for key in list(env.keys()):
                if 'CONDA' in key or 'LD_PRELOAD' in key:
                    removed_keys.append(key)
                    del env[key]
            
            # 只在使用 VAAPI 硬件加速时设置环境变量
            if use_gpu and enc_conf["encoder"] == "h264_vaapi":
                env['LIBVA_DRIVER_NAME'] = 'iHD'
                env['LIBVA_DRM_DEVICE'] = gpu_device or '/dev/dri/renderD128'  # 使用检测到的设备
                env['LIBVA_DRIVERS_PATH'] = '/usr/lib/x86_64-linux-gnu/dri'
                print(f"🔧 已设置 VAAPI 环境: device={env['LIBVA_DRM_DEVICE']}")
            
            if removed_keys:
                print(f"🔧 已清理环境变量: {', '.join(removed_keys)}")
            
            # 直接传递列表，不使用 shell=True
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg执行失败: {result.stderr}")
            
            print(f"✅ 视频生成成功: {output_path}")
            
            # 原子性重命名：.tmp -> .mp4（确保并发安全）
            if song_id and final_path:
                try:
                    # 使用 os.replace 而不是 os.rename，更安全（即使目标文件存在也会原子替换）
                    # 但在重命名前先检查是否有其他线程已经完成了
                    if not os.path.exists(final_path):
                        os.replace(output_path, final_path)
                        print(f"💾 视频已持久化存储: {final_path}")
                        output_path = final_path
                    else:
                        # 其他线程已经生成完成，删除当前的临时文件
                        print(f"ℹ️ 其他线程已完成视频生成，使用已有文件")
                        try:
                            os.remove(output_path)
                        except:
                            pass
                        output_path = final_path
                except FileExistsError:
                    # 竞争条件：其他线程已创建文件
                    print(f"ℹ️ 检测到并发生成，使用已有文件")
                    try:
                        os.remove(output_path)
                    except:
                        pass
                    output_path = final_path
                except Exception as e:
                    print(f"⚠️ 重命名失败: {e}")
                    # 即使重命名失败，临时文件仍然可用
            
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            return output_path
            
        except Exception as e:
            print(f"❌ 视频生成失败: {e}")
            # 清理临时文件和.tmp文件
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            if song_id and os.path.exists(output_path):
                try:
                    os.remove(output_path)  # 删除未完成的.tmp文件
                    print(f"🗑️ 已清理未完成的临时文件")
                except:
                    pass
            raise e
