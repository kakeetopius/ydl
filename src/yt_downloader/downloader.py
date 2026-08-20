import re
import yt_dlp
from enum import Enum
import shutil
import pathlib
import tempfile
import yt_downloader.helpers as helpers
from dataclasses import dataclass


class ContentType(Enum):
    VIDEO = 1
    AUDIO = 2
    BOTH = 3


@dataclass
class Options:
    format: str = ""
    music_dir: str = ""
    video_dir: str = ""
    download_playlist: bool = False
    list_formats: bool = False
    download_video: bool = False
    download_audio: bool = False
    download_both: bool = True
    verbose: bool = False
    port: int = 2210
    address: str = "localhost"


class Downloader:
    temp_path = pathlib.Path(tempfile.gettempdir())
    temp_dir: pathlib.Path

    def __init__(self, temp_dir="ydl"):
        temp = self.temp_path / temp_dir
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir(exist_ok=True, parents=True)

        self.temp_dir = temp

    def download_content(self, urls: list[str], opts: Options):
        """
        Function download_content downloads the youtube video pointed to by the urls given using yt_dlp module

        Parameters:
        urls: A list of one or more urls to youtube videos for downloading
        """

        content_type: ContentType = self.get_content_type(opts)

        music_path = ""
        video_path = ""

        ytdlp_format = ""
        music_format = ""
        video_format = ""

        if content_type == ContentType.AUDIO or content_type == ContentType.BOTH:
            music_format, music_path = self.get_music_opts(opts)
        if content_type == ContentType.VIDEO or content_type == ContentType.BOTH:
            video_format, video_path = self.get_video_opts(opts)

        if content_type == ContentType.VIDEO or content_type == ContentType.BOTH:
            ytdlp_format = video_format
        elif content_type == ContentType.AUDIO:
            ytdlp_format = music_format

        print(f"Format to download: {ytdlp_format}")
        opts.format = ytdlp_format

        ydl_opts = self.get_ytdlp_opts(opts, content_type)

        print("\nDownloading Content......................")
        self.download_with_ytdlp(urls, ydl_opts)
        self.save_files_to_correct_path(content_type, music_path, video_path)

    def download_with_ytdlp(self, urls: list[str], ydl_opts: dict):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
        except KeyboardInterrupt:
            return

    def list_ytdlp_formats(self, urls: list[str]):
        yt_dlp_opts = {"listformats": True}

        with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
            ydl.download(urls)

    def save_files_to_correct_path(
        self, content_type: ContentType, music_path: str, video_path: str
    ):
        pathlib.Path(music_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(video_path).mkdir(parents=True, exist_ok=True)

        for file in self.temp_dir.iterdir():
            if helpers.is_video_extension(file.suffix):
                if len(file.suffixes) > 1 and content_type == ContentType.BOTH:
                    # probably a temp video file with no audio
                    file.unlink(missing_ok=True)
                    continue
                file.move_into(video_path)
            elif helpers.is_audio_extension(file.suffix):
                if len(file.suffixes) > 1 and content_type == ContentType.BOTH:
                    # probably audio file that was merged into final video file. The file will have an extension like .f208.ext
                    file.move(
                        pathlib.Path(music_path) / Downloader.clean_file_name(file.name)
                    )
                    continue
                file.move_into(music_path)

        print("\nDownload(s) Successfull")
        if content_type == ContentType.AUDIO or content_type == ContentType.BOTH:
            print("Audio Files saved at: ", music_path)
        if content_type == ContentType.VIDEO or content_type == ContentType.BOTH:
            print("Video Files saved at: ", video_path)

    def get_content_type(self, opts: Options) -> ContentType:
        if opts.download_video:
            return ContentType.VIDEO
        elif opts.download_audio:
            return ContentType.AUDIO
        elif opts.download_both:
            return ContentType.BOTH

        video_dir_given = opts.video_dir != ""
        music_dir_given = opts.music_dir != ""

        if video_dir_given and music_dir_given:
            return ContentType.BOTH
        elif video_dir_given:
            return ContentType.VIDEO
        elif music_dir_given:
            return ContentType.AUDIO

        result = helpers.get_terminal_selection(
            message="Select Content Type to download:",
            selections=["Audio", "Video", "Both"],
            default=None,
        )
        if result == "Video":
            return ContentType.VIDEO
        elif result == "Audio":
            return ContentType.AUDIO
        else:
            return ContentType.BOTH

    def get_music_opts(self, opts: Options) -> tuple[str, str]:
        HOME = pathlib.Path.home()
        DEFAULT_MUSIC_PATH = HOME / "Music"

        if opts.music_dir != "":
            music_path = opts.music_dir
        else:
            # if music directory was not provided by user prompt the user for one or use default.
            m_path = helpers.get_dir_path("Enter music path(Leave blank for default): ")
            if m_path:
                music_path = m_path
            else:
                music_path = str(DEFAULT_MUSIC_PATH)
        music_format = "bestaudio"

        return (music_format, music_path)

    def get_video_opts(self, opts: Options) -> tuple[str, str]:
        HOME = pathlib.Path.home()
        DEFAULT_VIDEO_PATH = HOME / "Videos"

        if opts.video_dir != "":
            video_path = opts.video_dir
        else:
            # if video directory was not provided by user prompt the user for one or use default.
            v_path = helpers.get_dir_path("Enter video path(Leave blank for default): ")
            if v_path:
                video_path = v_path
            else:
                video_path = str(DEFAULT_VIDEO_PATH)

        if opts.format == "":
            formats = ["2160", "4320", "1440", "1080", "720", "480"]
            format = helpers.get_terminal_selection(
                "Choose format to download", formats, "720"
            )
            video_format = f"bestaudio+bestvideo[ext=mp4][height<={format}]/best[ext=m4a][height<={format}]"
        else:
            video_format = opts.format

        return (video_format, video_path)

    def get_ytdlp_opts(self, opts: Options, contentType: ContentType) -> dict:
        format_sorts = ["ext"]

        output_paths = {"home": str(self.temp_dir), "temp": str(self.temp_path)}

        output_format = {"default": "%(title)s.%(ext)s"}

        ydl_opts: dict = {
            "quiet": not opts.verbose,
            "format": opts.format,
            "format_sort": format_sorts,
            "concurrent_fragment_downloads": 5,
            "outtmpl": output_format,
            "paths": output_paths,
            "noplaylist": not opts.download_playlist,
        }
        if contentType == ContentType.BOTH:
            ydl_opts["keepvideo"] = True

        return ydl_opts

    @staticmethod
    def clean_file_name(name: str) -> str:
        """
        For yt-dlp temp files that are kept when downloading both audio and video at the same time, they will have extensions like .f903.ext.
        this func strips the .f903 part.
        """
        return re.sub(r"\.f\d+(?=\.[^.]+$)", "", name)
