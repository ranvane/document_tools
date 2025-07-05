import os
import sys

import cv2
import numpy as np
import wx
from loguru import logger

from card_correction_utils import card_correction


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
        # imencode默认期望输入的图像是 BGR 格式
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
        self.autoroate_checkbox = wx.CheckBox(self.panel, label="自动旋转")
        self.crop_btn = wx.Button(self.panel, label="保存当前裁剪区域（覆盖原图）")
        self.saveas_btn = wx.Button(self.panel, label="另存为...")
        self.prev_btn = wx.Button(self.panel, label="上一张")
        self.next_btn = wx.Button(self.panel, label="下一张")
        self.roateimage_btn = wx.Button(self.panel, label="旋转图片")

        # 定义 ONNX 模型文件的路径
        onnxmodel = get_model_path()
        # 加载 ONNX 模型
        # 创建 SCRFD 类的实例，传入 ONNX 模型路径、置信度阈值和 NMS 阈值
        self.card_net = card_correction(onnxmodel)

        self.orig_image = None  # 初始化原始图像，初始值为 None
        self.image_path = None  # 初始化图像文件路径，初始值为 None
        self.card_img = None  # 初始化当前显示的证件图像，初始值为 None
        self.crops = []  # 初始化裁剪区域列表，初始值为空列表
        self.selected_crop_idx = 0  # 初始化当前选中的裁剪区域索引，初始值为 0

        self.rotation_angle = 0  # 初始化旋转角度，用于记录图片的旋转角度，初始值为 0
        self.is_auto_roate = True  # 初始化是否自动旋转标志，初始值为 True，表示默认自动旋转

        self.autoroate_checkbox.SetValue(self.is_auto_roate)  # 设置复选框的初始状态，与 self.is_auto_roate 保持一致

        # 布局
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.select_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.prev_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.next_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.autoroate_checkbox, 0, wx.EXPAND | wx.ALL, 5)
        btn_sizer.Add(self.roateimage_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.crop_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.saveas_btn, 0, wx.ALL, 5)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.image_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.panel.SetSizer(main_sizer)

        # 拖拽支持，为面板设置拖拽目标，绑定拖拽文件的回调函数
        self.panel.SetDropTarget(MyFileDropTarget(self.on_drop_files))

        # 事件绑定
        self.select_btn.Bind(wx.EVT_BUTTON, self.on_select_file)
        self.crop_btn.Bind(wx.EVT_BUTTON, self.on_save_crop)
        self.saveas_btn.Bind(wx.EVT_BUTTON, self.on_save_as)
        self.prev_btn.Bind(wx.EVT_BUTTON, self.on_prev)
        self.next_btn.Bind(wx.EVT_BUTTON, self.on_next)
        self.roateimage_btn.Bind(wx.EVT_BUTTON, self.on_roateimage)

        self.crop_btn.Disable()  # 初始状态下禁用保存裁剪区域按钮
        self.saveas_btn.Disable()  # 初始状态下禁用另存为按钮
        self.prev_btn.Disable()  # 初始状态下禁用上一张按钮
        self.next_btn.Disable()  # 初始状态下禁用下一张按钮

        self.Centre()
        self.Show()

    def on_drop_files(self, paths):
        """
        处理文件拖拽事件，加载拖拽的文件。

        :param paths: 拖拽文件的路径，可能是单个路径字符串或路径列表
        """
        # 检查传入的路径是否为列表类型
        if isinstance(paths, list):
            # 若为列表，取列表中的第一个路径
            path = paths[0]
        else:
            # 若不是列表，直接使用传入的路径
            path = paths
        # 检查该路径是否指向一个有效的文件
        if os.path.isfile(path):
            # 若路径有效，调用 load_image 方法加载该文件
            self.load_image(path)

    def on_select_file(self, event):
        """
        处理选择图片按钮的点击事件，打开文件选择对话框让用户选择图像文件，
        并加载用户选择的图像文件。

        :param event: 按钮点击事件对象
        """
        # 创建一个文件选择对话框，设置对话框标题为“选择图像文件”，
        # 允许用户选择 JPG、PNG、JPEG 格式的文件，
        # 对话框样式为打开文件且文件必须存在
        with wx.FileDialog(self, "选择图像文件", wildcard="Image files (*.jpg;*.png;*.jpeg)|*.jpg;*.png;*.jpeg",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            # 显示文件选择对话框，若用户点击取消按钮，则返回
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            # 获取用户选择的文件路径
            path = fileDialog.GetPath()
            # 调用 load_image 方法加载用户选择的图像文件
            self.load_image(path)

    def load_image(self, path):
        """加载并显示图像文件"""
        self.image_path = path  # 保存图像路径
        # 重置相关状态
        self.orig_image = None  # 初始化原始图像，初始值为 None
        self.card_img = None  # 初始化当前显示的证件图像，初始值为 None
        self.crops = []  # 初始化裁剪区域列表，初始值为空列表
        self.selected_crop_idx = 0  # 初始化当前选中的裁剪区域索引，初始值为 0

        self.rotation_angle = 0  # 初始化旋转角度，用于记录图片的旋转角度，初始值为 0
        self.is_auto_roate = True  # 初始化是否自动旋转标志，初始值为 True，表示默认自动旋转
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
        out = self.card_net.infer(image)

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

    def show_crop(self, roate=False):
        self.card_img = self.crops[self.selected_crop_idx]
        if self.is_auto_roate:
            # 获取图片的高度和宽度
            height, width = self.card_img.shape[:2]
            # 若高度大于宽度，将图片向右旋转 90 度
            if height > width:
                self.card_img = cv2.rotate(self.card_img, cv2.ROTATE_90_CLOCKWISE)

        if roate:
            # 计算旋转次数
            rotate_count = self.rotation_angle // 90
            for _ in range(rotate_count):
                self.card_img = cv2.rotate(self.card_img, cv2.ROTATE_90_CLOCKWISE)

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

    def on_roateimage(self, event):
        # 在当前旋转角度基础上增加 90 度
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.show_crop(roate=True)

    def on_prev(self, event):
        if self.crops:
            self.selected_crop_idx = (self.selected_crop_idx - 1) % len(self.crops)
            self.show_crop()

    def on_next(self, event):
        if self.crops:
            self.selected_crop_idx = (self.selected_crop_idx + 1) % len(self.crops)
            self.show_crop()

    def on_save_crop(self, event):
        """
        处理保存当前选中裁剪区域并覆盖原图的事件。
        """
        try:
            # 检查是否存在裁剪区域，如果不存在则直接返回
            if not self.crops:
                return

            # 检查裁剪后的图像是否为空，若为空则显示错误信息并返回
            if self.card_img is None or self.card_img.size == 0:
                wx.MessageBox("裁剪后的图像为空，无法保存。", "错误", wx.OK | wx.ICON_ERROR)
                return

            # 检查文件路径是否有效，若无效则显示错误信息并返回
            if not self.image_path:
                wx.MessageBox("图像路径无效，无法保存。", "错误", wx.OK | wx.ICON_ERROR)
                return

            # 检查文件权限，尝试以追加模式打开文件
            try:
                with open(self.image_path, 'a'):
                    pass
            except Exception as e:
                # 若打开失败，显示权限不足或文件被占用的错误信息并返回
                wx.MessageBox(f"无法访问文件，可能是权限不足或文件被占用: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
                return

            # 保存图像，调用自定义函数处理中文路径保存问题
            success = save_image_with_chinese_path(self.image_path, self.card_img)

            if success:
                # 若保存成功，弹出消息框提示保存成功
                wx.MessageBox("裁剪区域已保存并覆盖原图。", "保存成功", wx.OK | wx.ICON_INFORMATION)
            else:
                # 如果保存失败，记录错误日志并显示包含路径和图像形状的错误信息
                logger.error(f"保存失败，路径: {self.image_path}, 图像形状: {self.card_img.shape}")
                wx.MessageBox(f"保存失败，路径: {self.image_path}, 图像形状: {self.card_img.shape}", "错误",
                              wx.OK | wx.ICON_ERROR)
        except Exception as e:
            # 捕获其他异常，记录错误日志并显示错误信息
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
        with wx.FileDialog(self, "另存为", defaultDir=default_dir,
                           wildcard="JPEG files (*.jpg)|*.jpg|PNG files (*.png)|*.png",
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
