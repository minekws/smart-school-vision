# Windows executable builds

Use Windows x64, Python 3.12, Git, and [uv](https://docs.astral.sh/uv/). Run the following commands from the repository root. The build script copies web assets from the Git index and bundles dependency notices from the build environment.

## Server

```powershell
$build = "$env:LOCALAPPDATA\SmartSchoolVisionWindowsBuild"
uv venv --python 3.12 "$build\server-venv"
$serverPython = "$build\server-venv\Scripts\python.exe"
uv pip install --python $serverPython -r requirements.txt 'pyinstaller==6.22.2'
& $serverPython windows_bundle/build.py server $build
```

## Camera

```powershell
$build = "$env:LOCALAPPDATA\SmartSchoolVisionWindowsBuild"
uv venv --python 3.12 "$build\camera-cpu-venv"
$cameraPython = "$build\camera-cpu-venv\Scripts\python.exe"
uv pip install --python $cameraPython --index https://download.pytorch.org/whl/cpu 'torch==2.11.0+cpu' 'torchvision==0.26.0+cpu'
uv pip install --python $cameraPython -r requirements.txt 'opencv-python==4.11.0.86' 'numpy==1.26.4' 'pillow==11.3.0' 'ultralytics==8.4.121' psutil jinja2 tqdm 'pyinstaller==6.22.2'
uv pip install --python $cameraPython --no-deps 'facenet-pytorch==2.6.0'
& $cameraPython windows_bundle/build.py camera $build
```

The executables appear in `dist` within the specified build directory. They are unsigned. They install dependency notices into `third-party-licenses` within the shared data directory at startup. The combined camera executable is distributed under AGPL-3.0 with Ultralytics. The original SmartSchool Vision source files also remain available under the repository's MIT license. Custom model weights, local face galleries, and account data stay outside the bundles.

Upstream source is available from [Ultralytics](https://github.com/ultralytics/ultralytics/tree/v8.4.121), [PyTorch](https://github.com/pytorch/pytorch/tree/v2.11.0), [torchvision](https://github.com/pytorch/vision/tree/v0.26.0), [FaceNet PyTorch](https://github.com/timesler/facenet-pytorch), and [PyInstaller](https://github.com/pyinstaller/pyinstaller/tree/v6.22.2).
