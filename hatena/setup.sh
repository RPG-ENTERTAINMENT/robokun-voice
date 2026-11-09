#!/bin/bash
# ffmpeg, Japanese fonts, Mesa (software OpenGL for EEVEE), Python 3.13 + bpy (in ~/hvenv)
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg fonts-noto-cjk fonts-noto-cjk-extra libegl1 libgl1 libgl1-mesa-dri libglx-mesa0 libxi6 libxkbcommon0 libxxf86vm1 libxfixes3 libxrender1 libsm6 > /dev/null
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.13
[ -d ~/hvenv ] || uv venv -p 3.13 ~/hvenv
uv pip install -p ~/hvenv/bin/python -q bpy numpy pillow cryptography google-api-python-client google-auth
fc-list | grep -i -m3 'NotoSansCJK'
