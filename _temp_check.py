import subprocess, json

result = subprocess.run([
    "yt-dlp", "--dump-json", "--no-playlist",
    "https://b23.tv/Qz9VX64"
], capture_output=True, text=True, timeout=30)

if result.returncode == 0:
    info = json.loads(result.stdout)
    print(f"duration={info.get('duration', 0)}s")
    print(f"title={info.get('title', '')}")
    print(f"uploader={info.get('uploader', '')}")
else:
    print(f"Error: {result.stderr}")
