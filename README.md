# 文档处理工具包

本项目包含两个实用脚本，用于处理文档图像的裁剪与合并操作。

## 功能介绍

### 1. 文档裁剪 (`document_cropper.py`)
- **功能**: 自动识别并裁剪文件中的证件，去除空白边距。
- **使用方法**:
  ```bash
  python document_cropper.py 
  ```


### 2. 文档图像合并 (`document_image_merger.py`)
- **功能**: 将多个图片文件合并为一个文档，并按字母顺序排序。
- **支持格式**: PNG, JPG/JPEG
- **使用方法**:
  ```bash
  python document_image_merger.py
  ```


## 安装依赖
确保已安装以下Python库：
```bash
pip install -r requirements.txt
```


## 使用
1.  `document_cropper.py` 对包含证件的图片进行裁剪，提取证件。
2.  `document_image_merger.py`将裁剪后的图像重新合并到A4纸上。


## 打包
使用PyInstaller打包为可执行文件:
```bash
pip install pyinstaller

pyinstaller -F -w   document_cropper.py
pyinstaller -F -w -i document_merger_icon.ico document_image_merger.py
pyinstaller -F -w -i imageMergerDoc_icon.png imageMergerDoc.py
```


## 版本信息
- Python版本要求: 3.x
- 测试环境: Windows/Linux/macOS

## 开源许可
MIT License

---

以上是基于提供的代码生成的README.md内容，如有需要可进一步扩展说明。
