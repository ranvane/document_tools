import wx
class FileDropTarget(wx.FileDropTarget):
    """实现文件拖放功能的辅助类"""

    def __init__(self, frame):
        """初始化目标 Frame"""
        super().__init__()
        self.frame = frame

    def OnDropFiles(self, x, y, filenames):
        """处理拖放文件事件，仅接受图片格式"""
        image_files = [f for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        self.frame.add_images(image_files)
        return True