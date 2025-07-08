
# 📄 简单证件裁剪、合并、图片展平、去阴影工具

本项目包含四个实用的文档图像处理脚本，支持证件自动裁剪与多图合并功能，适用于文档归档、打印整理等场景。

---

## ✨ 功能介绍

### 1. `document_card_cropper.py` – 证件裁剪工具
- **功能**：自动识别图像中的证件区域，裁剪并去除空白边缘。
- **使用方法**：
  ```bash
  python document_card_cropper.py
  ```

---

### 2. `document_image_merger.py` – 图像合并工具
- **功能**：将多个图片文件按文件名字母顺序合并排版至 A4 页面。
- **支持格式**：PNG、JPG/JPEG
- **使用方法**：
  ```bash
  python document_image_merger.py
  ```
### 3. `document_flatten_tool.py` – 图像展平、去模糊、去阴影工具
- **功能**：展平图像，去除模糊和阴影，提升文档阅读效果。
- **支持格式**：PNG、JPG/JPEG
- **使用方法**：
  ```bash
  python document_flatten_tool.py
  ```
- **注意**：该工具依赖于训练好的模型。
### 4. `imageMergerDoc.py` – 将图像合并工具生成的图片生成为word文档，以便打印。
- **功能**：将图像合并工具生成的图片生成为word文档，以便打印。
- **使用方法**：
  ```bash
  python imageMergerDoc.py
  ```


---

## 📦 安装依赖

确保你已经安装 Python 3，并使用以下命令安装必要依赖：

```bash
pip install -r requirements.txt
```

---

## 🔧 使用步骤

1. 使用 `document_card_cropper.py` 处理包含证件的图片，自动裁剪出证件区域。
2. 使用 `document_image_merger.py` 将裁剪后的图像合并排版成标准 A4 页面。
3. 使用 `document_flatten_tool.py` 展平图像并去除模糊和阴影。
4. 使用 `imageMergerDoc.py` 将图像合并工具生成的图片生成为word文档，以便打印。

---

## 🛠️ 打包为可执行文件

### ▶ 使用 PyInstaller 打包

#### 安装：
```bash
pip install pyinstaller
```

#### 示例命令：

```bash
# 通用打包（无图标）
pyinstaller -F -w document_card_cropper.py

# 带图标打包（推荐）
pyinstaller -F -w -i document_merger_icon.ico document_image_merger.py
pyinstaller -F -w -i imageMergerDoc_icon.ico imageMergerDoc.py
```
# document_card_cropper、document_flatten_tool打包
#### ⚠️ Windows 特殊处理：
```bash
# 避免 docx 导入错误
pyinstaller -F -w -i imageMergerDoc_icon.ico --hidden-import=docx imageMergerDoc.py

# 包含模型文件（Windows 分号分隔）
pyinstaller -F -w --icon=document_card_cropper.ico --add-data "models/card_correction.onnx;models" document_card_cropper.py

pyinstaller -F -w --icon=document_card_cropper.ico --add-data "models/drnet.onnx" --add-data "models/gcnet.onnx" --add-data "models/nafdpm.onnx" --add-data "models/unetcnn.onnx" --add-data "models/uvdoc.onnx"  document_flatten_tool.py
```

#### ✅ Linux 下打包：
```bash
# 注意：Linux 使用冒号分隔
pyinstaller -F -w --icon=document_card_cropper.ico --add-data "models/card_correction.onnx:models" document_card_cropper.py

pyinstaller -F -w --icon=document_merger_icon.ico --add-data "models/drnet.onnx:models" --add-data "models/gcnet.onnx:models" --add-data "models/nafdpm.onnx:models" --add-data "models/unetcnn.onnx:models" --add-data "models/uvdoc.onnx:models"  document_flatten_tool.py
```

---

## 🧪 使用 Nuitka 打包（实验性）

### 简单打包命令（需复制 models 文件夹至可执行文件同目录）：
```bash
nuitka --onefile   --windows-disable-console   --windows-icon-from-ico=document_card_cropper.ico   --include-data-dir=models=./models   document_card_cropper.py   --output-dir=nuitka_out
```

> 打包后大小约 96MB。需确保 `models` 文件夹位于同目录。

---

### 完整打包示例（带多参数）：

```bash
nuitka document_card_cropper.py   --jobs=0   --mingw64   --standalone   --onefile   --show-progress   --windows-console-mode=disable   --include-module=wx._xml   --include-data-files=document_card_cropper.png=.   --include-data-files=document_card_cropper.ico=.   --include-data-dir=models=models   --output-dir=nuitka_out
```

### ⏱️ 编译时间对比（i7-CPU 示例）：

| 参数 | real | user | sys |
|------|------|------|-----|
| `--jobs=0` | 3m47s | 11m13s | 23s |
| 默认并发 | 3m54s | 11m41s | 25s |

---

## 🧾 版本信息

- **Python 版本**：3.x
- **测试系统**：Windows 10 / Ubuntu 22.04

---

## 感谢 
本项目直接使用了一下项目的源代码和模型文件：
- [document-undistort-onnxrun](https://github.com/hpc203/document-undistort-onnxrun)
- [DocUnwrap](https://www.modelscope.cn/studios/jockerK/DocUnwrap/files)
- [cv_resnet_carddetection_scrfd34gkps-opencv-dnn](https://github.com/hpc203/cv_resnet_carddetection_scrfd34gkps-opencv-dnn)
- [读光-票证检测矫正模型](https://modelscope.cn/models/iic/cv_resnet18_card_correction)


