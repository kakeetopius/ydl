from yt_downloader import ydl

def main():
    try:
        ydl.start()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Quiting.............")
    except Exception as e:
        print(e)
    
