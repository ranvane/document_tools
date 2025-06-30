import os
import cv2
import wx
import numpy as np
from loguru import logger
from card_correction_utils import card_correction
import sys
 
def get_model_path():
    if hasattr(sys, '_MEIPASS'):
        # 如果程序是打包后的状态
        return os.path.join(sys._MEIPASS, os.path.join('models', 'card_correction.onnx'))
    else:
        # 如果是开发状态
        return os.path.join('models', 'card_correction.onnx')

# 提取保存图像的逻辑为独立函数
def save_image_with_chinese_path(image_path, cropped):
    success = False
    try:
        # 获取文件扩展名
        file_extension = os.path.splitext(image_path)[1].lower()
        #imencode默认期望输入的图像是 BGR 格式
        cropped = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR)
        if file_extension == '.jpg':
            _, buffer = cv2.imencode('.jpg', cropped)
        elif file_extension == '.png':
            _, buffer = cv2.imencode('.png', cropped)
        else:
            wx.MessageBox("不支持的文件格式，仅支持 .jpg 和 .png。", "错误", wx.OK | wx.ICON_ERROR)
            return success

        # 将编码后的字节流写入文件
        with open(image_path, 'wb') as f:
            f.write(buffer)
        success = True
    except Exception as e:
        logger.error(f"保存失败: {str(e)}")
    return success

class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def OnDropFiles(self, x, y, filenames):
        if filenames:
            self.callback(filenames)
        return True


class IDCardCropApp(wx.Frame):
    def __init__(self):
        super().__init__(None, title="证件裁剪器", size=(1000, 800))
        self.panel = wx.Panel(self)
        self.image_ctrl = wx.StaticBitmap(self.panel)
        self.select_btn = wx.Button(self.panel, label="选择图片")
        self.crop_btn = wx.Button(self.panel, label="保存当前裁剪区域（覆盖原图）")
        self.saveas_btn = wx.Button(self.panel, label="另存为...")
        self.prev_btn = wx.Button(self.panel, label="上一张")
        self.next_btn = wx.Button(self.panel, label="下一张")
        
        # 定义 ONNX 模型文件的路径
        onnxmodel = get_model_path()
        # 加载 ONNX 模型
        # 创建 SCRFD 类的实例，传入 ONNX 模型路径、置信度阈值和 NMS 阈值
        self.card_net = card_correction(onnxmodel)

        self.orig_image = None
        self.image_path = None
        self.card_img=None
        self.crops=[]
        self.selected_crop_idx=0

        # 布局
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.select_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.prev_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.next_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.crop_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.saveas_btn, 0, wx.ALL, 5)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.image_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.panel.SetSizer(main_sizer)

        # 拖拽支持
        self.panel.SetDropTarget(MyFileDropTarget(self.on_drop_files))

        # 事件绑定
        self.select_btn.Bind(wx.EVT_BUTTON, self.on_select_file)
        self.crop_btn.Bind(wx.EVT_BUTTON, self.on_save_crop)
        self.saveas_btn.Bind(wx.EVT_BUTTON, self.on_save_as)
        self.prev_btn.Bind(wx.EVT_BUTTON, self.on_prev)
        self.next_btn.Bind(wx.EVT_BUTTON, self.on_next)

        self.crop_btn.Disable()
        self.saveas_btn.Disable()
        self.prev_btn.Disable()
        self.next_btn.Disable()

        self.Centre()
        self.Show()
        
        

    def on_drop_files(self, paths):
        if isinstance(paths, list):
            path = paths[0]
        else:
            path = paths
        if os.path.isfile(path):
            self.load_image(path)

    def on_select_file(self, event):
        with wx.FileDialog(self, "选择图像文件", wildcard="Image files (*.jpg;*.png;*.jpeg)|*.jpg;*.png;*.jpeg",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            path = fileDialog.GetPath()
            self.load_image(path)

    def load_image(self, path):
        """加载并显示图像文件"""
        self.image_path = path  # 保存图像路径
        # 重置相关状态
        self.crops = []
        self.selected_crop_idx = 0
        self.card_img = None
        try:
            # 使用numpy的fromfile配合imdecode解决中文路径问题
            img_array = np.fromfile(path, dtype=np.uint8)
            self.orig_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            wx.MessageBox(f"无法加载图像: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            return
        if self.orig_image is None:
            # 图像加载失败时显示错误提示
            wx.MessageBox("无法加载图像。请确认文件格式正确。", "错误", wx.OK | wx.ICON_ERROR)
            return
        # 检测并显示图像中的裁剪区域
        self.detect_and_show_crops()
        # 启用裁剪和另存为按钮
        self.crop_btn.Enable()
        self.saveas_btn.Enable()

    def detect_and_show_crops(self):
        image = self.orig_image.copy()
        
        # 调用 大模型 对读取的图像进行目标检测，返回提取好的图片
        out= self.card_net.infer(image)
        processed_img_rgb=None
        # 假设只显示处理后的第一张图像
        for _out in out['OUTPUT_IMGS']:
            _out_rgb = cv2.cvtColor(_out, cv2.COLOR_BGR2RGB)
            self.crops.append(_out_rgb)
        
        if self.crops:
            self.show_crop()
            self.prev_btn.Enable()
            self.next_btn.Enable()
        else:
            wx.MessageBox("未检测到矩形证件区域。", "提示", wx.OK | wx.ICON_INFORMATION)
            self.crop_btn.Disable()
            self.saveas_btn.Disable()
            self.prev_btn.Disable()
            self.next_btn.Disable()

    def show_crop(self):
        self.card_img=self.crops[self.selected_crop_idx]
        # 获取输出图像的原始高度和宽度
        orig_h, orig_w = self.card_img.shape[:-1]
        print("输出图像尺寸:", self.card_img.shape)

        # 设定最大显示尺寸
        max_width = 800
        max_height = 600

        # 计算缩放比例
        width_ratio = max_width / orig_w
        height_ratio = max_height / orig_h
        scale_ratio = min(width_ratio, height_ratio)

        # 计算调整后的尺寸
        new_w = int(orig_w * scale_ratio)
        new_h = int(orig_h * scale_ratio)

        # 调整图像大小
        resized_img = cv2.resize(self.card_img, (new_w, new_h))

        # 使用 wxPython 的 Image 类创建一个图像对象，传入图像的宽度、高度和字节数据
        image = wx.Image(new_w, new_h, resized_img.tobytes())
        # 将 wx.Image 对象转换为 wx.Bitmap 对象
        bitmap = wx.Bitmap(image)
        # 设置 Bitmap 到静态位图控件
        self.image_ctrl.SetBitmap(bitmap)
        # 根据图像尺寸调整 self.image_ctrl 的大小
        self.image_ctrl.SetSize((new_w, new_h))
        # 重新布局面板，确保界面元素正确显示
        self.panel.Layout()
        # 更新窗口标题，显示当前选中的裁剪区域序号和总裁剪区域数量
        self.SetTitle(f"证件裁剪器 - 当前区域 {self.selected_crop_idx + 1} / {len(self.crops)}")

    def on_prev(self, event):
        if self.crops:
            self.selected_crop_idx = (self.selected_crop_idx - 1) % len(self.crops)
            self.show_crop()

    def on_next(self, event):
        if self.crops:
            self.selected_crop_idx = (self.selected_crop_idx + 1) % len(self.crops)
            self.show_crop()

    def on_save_crop(self, event):
        try:
            if not self.crops:
                return
            cropped = self.crops[self.selected_crop_idx]


            # 检查裁剪后的图像是否为空
            if cropped is None or cropped.size == 0:
                wx.MessageBox("裁剪后的图像为空，无法保存。", "错误", wx.OK | wx.ICON_ERROR)
                return

            # 检查文件路径是否有效
            if not self.image_path:
                wx.MessageBox("图像路径无效，无法保存。", "错误", wx.OK | wx.ICON_ERROR)
                return

            # 检查文件权限
            try:
                with open(self.image_path, 'a'):
                    pass
            except Exception as e:
                wx.MessageBox(f"无法访问文件，可能是权限不足或文件被占用: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
                return

            # 保存图像
            # success = cv2.imwrite(self.image_path, cropped)
            # 处理中文路径保存问题
            success = save_image_with_chinese_path(self.image_path, cropped)

            if success:
                wx.MessageBox("裁剪区域已保存并覆盖原图。", "保存成功", wx.OK | wx.ICON_INFORMATION)
            else:
                # 如果保存失败，显示包含路径和图像形状的错误信息
                logger.error(f"保存失败，路径: {self.image_path}, 图像形状: {cropped.shape}")
                wx.MessageBox(f"保存失败，路径: {self.image_path}, 图像形状: {cropped.shape}", "错误", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            logger.error(f"保存失败: {str(e)}")
            wx.MessageBox(f"保存失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)

    def on_save_as(self, event):
        # 复制裁剪后的图像，避免修改原始图像数据
        cropped = self.card_img.copy()

        # 获取输入文件所在的文件夹路径
        if self.image_path:
            default_dir = os.path.dirname(self.image_path)
        else:
            default_dir = ""

        # 打开文件保存对话框，让用户选择保存路径和文件格式
        # 支持 JPEG 和 PNG 两种文件格式
        with wx.FileDialog(self, "另存为", defaultDir=default_dir, wildcard="JPEG files (*.jpg)|*.jpg|PNG files (*.png)|*.png",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            # 显示文件对话框，如果用户点击取消按钮，则直接返回
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            # 获取用户选择的保存路径
            save_path = fileDialog.GetPath()
            # 获取用户选择的通配符索引，用于确定文件类型
            wildcard_index = fileDialog.GetFilterIndex()
            # 根据通配符索引判断文件类型
            if wildcard_index == 0:  # JPEG 文件
                # 若保存路径不以 .jpg 结尾，则自动添加 .jpg 扩展名
                if not save_path.lower().endswith('.jpg'):
                    save_path += '.jpg'
            elif wildcard_index == 1:  # PNG 文件
                # 若保存路径不以 .png 结尾，则自动添加 .png 扩展名
                if not save_path.lower().endswith('.png'):
                    save_path += '.png'

            # 调用自定义函数将裁剪后的图像保存到指定路径
            # 该函数支持中文路径的保存操作
            success = save_image_with_chinese_path(save_path, cropped)
            if success:
                # 若保存成功，弹出消息框显示保存路径
                wx.MessageBox(f"已保存至：{save_path}", "保存成功", wx.OK | wx.ICON_INFORMATION)
            else:
                # 若保存失败，弹出消息框提示保存失败
                wx.MessageBox("保存失败。", "错误", wx.OK | wx.ICON_ERROR)


if __name__ == "__main__":
    app = wx.App(False)
    frame = IDCardCropApp()
    app.MainLoop()
