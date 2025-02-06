import os
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path
from spleeter.separator import Separator

def is_video_file(file_path):
    """
    判断输入文件是否为视频文件。

    参数:
    - file_path (str): 文件路径。

    返回:
    - bool: 如果文件包含视频流，返回 True；否则 False。
    """
    # 使用 ffprobe 检查是否含有视频流
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return 'video' in result.stdout.lower()
    except subprocess.CalledProcessError:
        return False

def extract_audio(input_path, output_audio_path):
    """
    使用 FFmpeg 从视频文件中提取音频。

    参数:
    - input_path (str): 输入视频文件路径。
    - output_audio_path (str): 输出音频文件路径。
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-q:a", "0",
        "-map", "a",
        output_audio_path,
        "-y"  # 强制覆盖
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def create_silent_video(duration, output_video_path):
    """
    创建一个静音的视频文件，长度与音频相同。

    参数:
    - duration (float): 视频时长（秒）。
    - output_video_path (str): 输出视频文件路径。
    """
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1280x720:d={duration}",
        "-c:v", "libx264",
        "-t", f"{duration}",
        "-y",
        output_video_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def combine_audio_with_video(input_video, vocals_audio, accompaniment_audio, output_video_path):
    """
    将分离出的双音轨嵌入到视频文件中，生成包含双音轨的视频。

    参数:
    - input_video (str): 原始视频文件路径。
    - vocals_audio (str): 分离出的人声音轨路径。
    - accompaniment_audio (str): 分离出的伴奏音轨路径。
    - output_video_path (str): 输出视频文件路径。
    """
    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-i", vocals_audio,
        "-i", accompaniment_audio,
        "-map", "0:v",
        "-map", "1:a",
        "-map", "2:a",
        "-c:v", "copy",  # 复制视频流
        "-c:a", "aac",   # 使用 AAC 编码音频流
        "-metadata:s:a:0", "title=Vocals",
        "-metadata:s:a:1", "title=Accompaniment",
        output_video_path,
        "-y"  # 强制覆盖
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def combine_audio_into_multitrack(input_audio, vocals_audio, accompaniment_audio, output_audio_path):
    """
    将分离出的双音轨合并为一个多音轨的音频文件（MKV 格式）。

    参数:
    - input_audio (str): 原始音频文件路径（可选，根据需要）。
    - vocals_audio (str): 分离出的人声音轨路径。
    - accompaniment_audio (str): 分离出的伴奏音轨路径。
    - output_audio_path (str): 输出多音轨音频文件路径。
    """
    cmd = [
        "ffmpeg",
        "-i", input_audio,            # 输入原音频
        "-i", accompaniment_audio,     # 输入伴奏音轨
        "-c:a:0", "aac",               # 使用 AAC 编码第一个音轨
        "-b:a:0", "192k",              # 设置第一个音轨的比特率
        "-c:a:1", "aac",               # 使用 AAC 编码第二个音轨
        "-b:a:1", "192k",              # 设置第二个音轨的比特率
        "-map", "0:a",                 # 映射第一个音轨（原声）
        "-map", "1:a",                 # 映射第二个音轨（伴奏）
        "-metadata:s:a:0", "title=Vocals",
        "-metadata:s:a:1", "title=Accompaniment",
        output_audio_path,             # 输出文件路径
        "-y"                           # 强制覆盖输出文件
    ]
    print(f"运行 FFmpeg 命令: {' '.join(cmd)}")
    process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("FFmpeg stderr:", process.stderr.decode())

def separate_audio(input_audio_path, output_dir):
    """
    使用 Spleeter 分离音频为人声和伴奏。

    参数:
    - input_audio_path (str): 输入音频文件路径。
    - output_dir (str): 输出目录路径。

    返回:
    - vocals_path (str): 分离出的人声音轨路径。
    - accompaniment_path (str): 分离出的伴奏音轨路径。
    """
    separator = Separator('spleeter:2stems')
    separator.separate_to_file(input_audio_path, output_dir)

    # Spleeter 默认将分离后的文件放在一个与原音频同名的子目录中
    base_name = os.path.splitext(os.path.basename(input_audio_path))[0]
    separated_dir = os.path.join(output_dir, base_name)

    vocals_path = os.path.join(separated_dir, "vocals.wav")
    accompaniment_path = os.path.join(separated_dir, "accompaniment.wav")

    if not os.path.isfile(vocals_path) or not os.path.isfile(accompaniment_path):
        raise FileNotFoundError("Spleeter 分离音频失败，未找到分离后的音轨。")

    return vocals_path, accompaniment_path

def get_audio_duration(audio_path):
    """
    获取音频文件的时长（秒）。

    参数:
    - audio_path (str): 音频文件路径。

    返回:
    - float: 音频时长（秒）。
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())

def process_video(input_path, output_path, temp_dir):
    """
    处理视频文件：提取音频、分离、合并双音轨回视频。

    参数:
    - input_path (str): 输入视频文件路径。
    - output_path (str): 输出双音轨视频文件路径。
    - temp_dir (str): 临时目录路径。
    """
    original_audio = os.path.join(temp_dir, "original_audio.wav")
    
    # 提取音频
    print("正在提取视频中的音频...")
    extract_audio(input_path, original_audio)
    
    # 分离音频
    print("正在分离音频轨道 (人声和伴奏)...")
    vocals, accompaniment = separate_audio(original_audio, temp_dir)
    
    # 合并双音轨回视频
    print("正在合并双音轨回视频文件...")
    combine_audio_with_video(input_path, vocals, accompaniment, output_path)
    print(f"双音轨视频已生成: {output_path}")

def process_audio(input_path, output_path, temp_dir):
    """
    处理音频文件：分离、合并为多音轨音频或嵌入静态视频。

    参数:
    - input_path (str): 输入音频文件路径。
    - output_path (str): 输出文件路径（音频或视频）。
    - temp_dir (str): 临时目录路径。
    """
    print("正在分离音频轨道 (人声和伴奏)...")
    vocals, accompaniment = separate_audio(input_path, temp_dir)
    
    # 判断输出文件格式
    output_ext = os.path.splitext(output_path)[1].lower()
    if output_ext in ['.mkv', '.mp4']:
        # 合并为多音轨的 MKV 文件（使用 MKV 更适合多音轨）
        print("正在合并双音轨为多音轨音频文件 (MKV)...")
        if output_ext == '.mp4':
            print("注意: MP4 格式支持双音轨有限，建议使用 MKV 格式。")
        combine_audio_into_multitrack(input_path ,vocals, accompaniment, output_path)
    elif output_ext in ['.mp3', '.wav', '.aac']:
        # 对于仅音频格式，无法直接存储多音轨，建议输出为 MKV 或视频格式
        raise ValueError("仅音频格式不支持多音轨输出。请使用 MKV、MP4 或其他支持多音轨的容器格式。")
    elif output_ext in ['.avi', '.mov']:
        # 可选择嵌入静态视频
        print("正在创建带有双音轨的静态视频文件...")
        duration = get_audio_duration(input_path)
        silent_video = os.path.join(temp_dir, "silent_video.mp4")
        create_silent_video(duration, silent_video)
        combine_audio_with_video(silent_video, vocals, accompaniment, output_path)
    else:
        raise ValueError(f"不支持的输出文件格式: {output_ext}")
    
    print(f"双音轨文件已生成: {output_path}")

def separate_and_merge(input_path, output_path):
    """
    主函数：根据输入文件类型处理视频或音频文件。

    参数:
    - input_path (str): 输入文件路径（视频或音频）。
    - output_path (str): 输出文件路径。
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    # 创建一个临时目录用于存储中间文件
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if is_video_file(input_path):
                print("检测到输入文件为视频文件。")
                process_video(input_path, output_path, temp_dir)
            else:
                print("检测到输入文件为音频文件。")
                process_audio(input_path, output_path, temp_dir)
        except subprocess.CalledProcessError as e:
            print("FFmpeg 命令执行失败。")
            print(e.stderr.decode())
            raise e
        except Exception as e:
            print("发生错误:", str(e))
            raise e

def main():
    """
    脚本入口，处理命令行参数。
    """
    if len(sys.argv) != 3:
        print("用法: python separate_and_merge.py <输入文件路径> <输出文件路径>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        separate_and_merge(input_file, output_file)
    except Exception as error:
        print(f"处理失败: {error}")
        sys.exit(1)

if __name__ == "__main__":
    # main()
    separate_and_merge("work-dir/江南-林俊杰.96.mp3", "work-dir/江南-林俊杰.96-new.mkv")
