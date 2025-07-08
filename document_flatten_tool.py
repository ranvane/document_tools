import os
import sys
import cv2
import numpy as np
import wx
import time
from loguru import logger

from document_undistort.binary_predictor import UnetCNN
from document_undistort.unblur_predictor import NAF_DPM, OpenCvBilateral
from document_undistort.unshadow_predictor import GCDRNET
from document_undistort.unwrap_predictor import UVDocPredictor
import threading


def get_model_path(name):
    if hasattr(sys, '_MEIPASS'):
        # 如果程序是打包后的状态
        return os.path.join(sys._MEIPASS, os.path.join('models', name))
    else:
        # 如果是开发状态
        return os.path.join('models', name)


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


class document_Flatten_Tool(wx.Frame):
    def __init__(self):
        super().__init__(None, title="文档展平、漂白", size=(1000, 800))
        self.panel = wx.Panel(self)
        self.image_ctrl = wx.StaticBitmap(self.panel)
        self.select_btn = wx.Button(self.panel, label="选择图片")

        self.crop_btn = wx.Button(self.panel, label="保存当前裁剪区域（覆盖原图）")
        self.saveas_btn = wx.Button(self.panel, label="另存为...")

        # 创建复选框
        self.unblur_checkbox = wx.CheckBox(self.panel, label="NAF_DPM去模糊")
        self.unblur_checkbox.SetToolTip("勾选此项将处理时间会大幅延长！")
        self.unblur_checkbox.Bind(wx.EVT_CHECKBOX, self.on_checkbox_change)

        # 定义 ONNX 模型文件的路径，创建 模型类的实例，传入 ONNX 模型路径、置信度阈值和 NMS 阈值
        # 创建二值化模型实例，使用 UnetCNN 模型处理图像，实现图像二值化操作
        binary_model = UnetCNN(get_model_path('unetcnn.onnx'))
        # 创建去模糊模型实例，使用 NAF_DPM 模型对图像进行去模糊处理，提升图像清晰度
        unblur_model = NAF_DPM(get_model_path('nafdpm.onnx'))
        # 创建另一个去模糊模型实例，使用 OpenCV 的双边滤波等方法对图像进行去模糊处理
        unblur_model2 = OpenCvBilateral()
        # 创建去阴影模型实例，结合 GCNet 和 DRNet 模型去除图像中的阴影
        unshadow_model = GCDRNET(get_model_path('gcnet.onnx'), get_model_path('drnet.onnx'))
        # 创建文档展开模型实例，使用 UVDocPredictor 模型对文档图像进行展开操作
        unwrap_model = UVDocPredictor(get_model_path('uvdoc.onnx'))
        self.model_dict = {
            "binary": binary_model,
            "unblur": unblur_model,
            "unshadow": unshadow_model,
            "unwrap": unwrap_model,
            "OpenCvBilateral": unblur_model2
        }

        # 根据复选框初始状态设置 task_list
        self.on_checkbox_change(None)

        self.orig_image = None  # 初始化原始图像，初始值为 None
        self.image_path = None  # 初始化图像文件路径，初始值为 None
        self.doc_img = None  # 初始化当前显示的证件图像，初始值为 None



        # 布局
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.select_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.crop_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.saveas_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.unblur_checkbox, 0, wx.ALL, 5)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.image_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.panel.SetSizer(main_sizer)

        # 创建状态栏
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetStatusText("就绪")

        # 拖拽支持，为面板设置拖拽目标，绑定拖拽文件的回调函数
        self.panel.SetDropTarget(MyFileDropTarget(self.on_drop_files))

        # 事件绑定
        self.select_btn.Bind(wx.EVT_BUTTON, self.on_select_file)
        self.crop_btn.Bind(wx.EVT_BUTTON, self.on_save_crop)
        self.saveas_btn.Bind(wx.EVT_BUTTON, self.on_save_as)


        self.crop_btn.Disable()  # 初始状态下禁用保存裁剪区域按钮
        self.saveas_btn.Disable()  # 初始状态下禁用另存为按钮


        self.Centre()
        self.Show()

    def on_checkbox_change(self, event):
        if self.unblur_checkbox.IsChecked():
            self.task_list = ["unwrap", "unshadow", "unblur", "OpenCvBilateral"]
        else:
            self.task_list = ["unwrap", "unshadow", "OpenCvBilateral"]

    def on_drop_files(self, paths):
        """
        处理文件拖拽事件，加载拖拽的文件。

        :param paths: 拖拽文件的路径，可能是单个路径字符串或路径列表
        """
        self.status_bar.SetStatusText("正在处理拖拽文件...")
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
        self.doc_img = None  # 初始化当前显示的证件图像，初始值为 None

        try:
            # 使用numpy的fromfile配合imdecode解决中文路径问题
            img_array = np.fromfile(path, dtype=np.uint8)
            self.orig_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            wx.MessageBox(f"无法加载图像: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            self.status_bar.SetStatusText("图像加载失败")
            return
        if self.orig_image is None:
            # 图像加载失败时显示错误提示
            wx.MessageBox("无法加载图像。请确认文件格式正确。", "错误", wx.OK | wx.ICON_ERROR)
            self.status_bar.SetStatusText("无法加载图像。请确认文件格式正确。")
            return
        # 检测并显示图像中的裁剪区域
        self.detect_and_show_crops()
        # 启用裁剪和另存为按钮
        self.crop_btn.Enable()
        self.saveas_btn.Enable()
        self.status_bar.SetStatusText("图像加载成功")

    def detect_and_show_crops(self):
        # 直接对 self.orig_image 进行颜色空间转换
        srcimg_rgb = cv2.cvtColor(self.orig_image, cv2.COLOR_BGR2RGB)
        # 直接复制 self.orig_image 给 out_img
        out_img = self.orig_image.copy()
        self.status_bar.SetStatusText("开始漂白、展平图片...")

        # 记录模型推理开始时间
        start_time = time.time()
        # 启动子线程进行模型推理
        thread = threading.Thread(target=self.run_model_inference, args=(out_img, start_time))
        thread.start()

    def run_model_inference(self, out_img, start_time):
        model_execution_times = {}
        for task in self.task_list:
            # 记录每个模型开始执行的时间
            task_start_time = time.time()

            out_img = self.model_dict[task].predict(out_img)
            # 记录每个模型结束执行的时间
            task_end_time = time.time()
            # 计算每个模型的执行时长
            execution_time = task_end_time - task_start_time
            model_execution_times[task] = execution_time
            logger.info(f"{task} 模型执行时长: {execution_time:.4f} 秒")

        self.doc_img = cv2.cvtColor(out_img, cv2.COLOR_BGR2RGB)
        # 记录模型推理结束时间
        end_time = time.time()
        # 计算总处理时间
        total_processing_time = end_time - start_time

        # 使用 wx.CallAfter 在主线程中更新 UI，并传递总处理时间
        wx.CallAfter(self.update_ui_after_inference, total_processing_time)

    def update_ui_after_inference(self, total_processing_time):
        if self.doc_img is not None:
            self.show_crop()
            # 在状态栏信息中加入处理时间
            self.status_bar.SetStatusText(f"文档已展开、漂白。处理时间: {total_processing_time:.2f} 秒")
        else:
            wx.MessageBox("文档展开、漂白失败。", "提示", wx.OK | wx.ICON_INFORMATION)
            self.status_bar.SetStatusText("文档展开、漂白失败。")



    def show_crop(self, roate=False):
        # 获取输出图像的原始高度和宽度
        orig_h, orig_w = self.doc_img.shape[:-1]
        logger.info("输出图像尺寸:", self.doc_img.shape)

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
        resized_img = cv2.resize(self.doc_img, (new_w, new_h))

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
        self.SetTitle(f"文档展平、漂白")


    def on_save_crop(self, event):
        """
        处理保存当前选中裁剪区域并覆盖原图的事件。
        """
        try:


            # 检查裁剪后的图像是否为空，若为空则显示错误信息并返回
            if self.doc_img is None or self.doc_img.size == 0:
                wx.MessageBox("处理后的图像为空，无法保存。", "错误", wx.OK | wx.ICON_ERROR)
                self.status_bar.SetStatusText("保存失败：处理后的图像为空")
                return

            # 检查文件路径是否有效，若无效则显示错误信息并返回
            if not self.image_path:
                wx.MessageBox("图像路径无效，无法保存。", "错误", wx.OK | wx.ICON_ERROR)
                self.status_bar.SetStatusText("保存失败：图像路径无效")
                return

            # 检查文件权限，尝试以追加模式打开文件
            try:
                with open(self.image_path, 'a'):
                    pass
            except Exception as e:
                # 若打开失败，显示权限不足或文件被占用的错误信息并返回
                wx.MessageBox(f"无法访问文件，可能是权限不足或文件被占用: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
                self.status_bar.SetStatusText("保存失败：文件访问受限")
                return

            # 保存图像，调用自定义函数处理中文路径保存问题
            success = save_image_with_chinese_path(self.image_path, self.doc_img)

            if success:
                # 若保存成功，弹出消息框提示保存成功
                wx.MessageBox("已保存并覆盖原图。", "保存成功", wx.OK | wx.ICON_INFORMATION)
                self.status_bar.SetStatusText("保存成功。")
            else:
                # 如果保存失败，记录错误日志并显示包含路径和图像形状的错误信息
                logger.error(f"保存失败，路径: {self.image_path}, 图像形状: {self.doc_img.shape}")
                wx.MessageBox(f"保存失败，路径: {self.image_path}, 图像形状: {self.doc_img.shape}", "错误",
                              wx.OK | wx.ICON_ERROR)
                self.status_bar.SetStatusText("保存失败。")
        except Exception as e:
            # 捕获其他异常，记录错误日志并显示错误信息
            logger.error(f"保存失败: {str(e)}")
            wx.MessageBox(f"保存失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            self.status_bar.SetStatusText("保存失败：发生异常")
        finally:
            self.status_bar.SetStatusText("就绪")

    def on_save_as(self, event):
        # 复制裁剪后的图像，避免修改原始图像数据
        cropped = self.doc_img.copy()

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
                self.status_bar.SetStatusText("就绪")
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
                self.status_bar.SetStatusText("另存为成功")
            else:
                # 若保存失败，弹出消息框提示保存失败
                wx.MessageBox("保存失败。", "错误", wx.OK | wx.ICON_ERROR)
                self.status_bar.SetStatusText("另存为失败")
        self.status_bar.SetStatusText("就绪")


if __name__ == "__main__":
    app = wx.App(False)
    frame = document_Flatten_Tool()
    app.MainLoop()
