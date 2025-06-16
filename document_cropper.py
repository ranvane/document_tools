import os
import cv2
import wx
import numpy as np
from loguru import logger
from utils import SCRFD,preprocess_image
import sys
 
def get_model_path():
    if hasattr(sys, '_MEIPASS'):
        # 如果程序是打包后的状态
        return os.path.join(sys._MEIPASS, os.path.join('models', 'carddetection_scrf.onnx'))
    else:
        # 如果是开发状态
        return os.path.join('models', 'carddetection_scrf.onnx')

# 提取保存图像的逻辑为独立函数
def save_image_with_chinese_path(image_path, cropped):
    success = False
    try:
        # 获取文件扩展名
        file_extension = os.path.splitext(image_path)[1].lower()
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
        self.card_net = SCRFD(onnxmodel)

        self.orig_image = None
        self.image_path = None
        self.crops = []
        self.selected_crop_idx = 0

        # 布局
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.select_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.prev_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.next_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.crop_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.saveas_btn, 0, wx.ALL, 5)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.image_ctrl, 1, wx.EXPAND | wx.ALL, 10)
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
        # gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # edged = cv2.Canny(blurred, 50, 150)
        # 1. 图像预处理
        _, blurred = preprocess_image(image)
        if blurred is None:
            logger.error("图像预处理失败，无法进行后续操作")
            wx.MessageBox("图像预处理失败。", "错误", wx.OK | wx.ICON_ERROR)
            return None

        # # 2. 边缘检测

        # edged = cv2.Canny(blurred, 50, 150)

        # # 3. 轮廓检测与筛选
        # contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # self.crops = []

        # for cnt in contours:
        #     approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        #     if len(approx) == 4 and cv2.contourArea(cnt) > 5000:
        #         x, y, w, h = cv2.boundingRect(cnt)
        #         self.crops.append((x, y, w, h))
        
        # 调用 SCRFD 实例的 detect 方法对读取的图像进行目标检测
        outimg, corner_points_list = self.card_net.detect(image)
        self.crops = []
        # 遍历检测到的目标的四个角点坐标
        print(f"图像 {self.image_path} 的检测到{len(corner_points_list)}个目标,四个角点坐标分别为: {corner_points_list}")
        for corner_points in corner_points_list:
            # 提取 xmin, ymin, xmax, ymax
            xmin = min([point[0] for point in corner_points])
            ymin = min([point[1] for point in corner_points])
            xmax = max([point[0] for point in corner_points])
            ymax = max([point[1] for point in corner_points])

            # 计算宽度和高度
            w = xmax - xmin
            h = ymax - ymin

            # 将 (x, y, w, h) 添加到 self.crops
            self.crops.append((xmin, ymin, w, h))

            print(f"图像 {self.image_path} 的检测目标四个角点坐标: {corner_points}")


        if self.crops:
            print(self.crops)
            self.selected_crop_idx = 0
            self.show_crop()
            if len(self.crops) > 1:
                self.prev_btn.Enable()
                self.next_btn.Enable()
        else:
            wx.MessageBox("未检测到矩形证件区域。", "提示", wx.OK | wx.ICON_INFORMATION)
            self.crop_btn.Disable()
            self.saveas_btn.Disable()
            self.prev_btn.Disable()
            self.next_btn.Disable()

    def show_crop(self):
        x, y, w, h = self.crops[self.selected_crop_idx]
        cropped = self.orig_image[y:y + h, x:x + w]
        resized = cv2.resize(cropped, (800, 500))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        image = wx.Image(w, h, rgb.tobytes())
        self.image_ctrl.SetBitmap(wx.Bitmap(image))
        self.panel.Layout()
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
            x, y, w, h = self.crops[self.selected_crop_idx]
            cropped = self.orig_image[y:y + h, x:x + w]

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
            success =save_image_with_chinese_path(self.image_path, cropped)

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
        # Check if there are detected crop areas
        if not self.crops:
            return
        # Get the coordinates and dimensions of the currently selected crop area
        x, y, w, h = self.crops[self.selected_crop_idx]
        # Crop the corresponding area from the original image
        cropped = self.orig_image[y:y + h, x:x + w]

        # Open a file save dialog for the user to choose the save path and file format
        with wx.FileDialog(self, "另存为", wildcard="JPEG files (*.jpg)|*.jpg|PNG files (*.png)|*.png",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            # Show the file dialog; if the user clicks Cancel, return
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            # Get the save path selected by the user
            save_path = fileDialog.GetPath()
            # Get the selected wildcard index to determine the file type
            wildcard_index = fileDialog.GetFilterIndex()
            if wildcard_index == 0:  # JPEG files
                if not save_path.lower().endswith('.jpg'):
                    save_path += '.jpg'
            elif wildcard_index == 1:  # PNG files
                if not save_path.lower().endswith('.png'):
                    save_path += '.png'

            # Use OpenCV's imwrite function to save the cropped image to the specified path
            success =save_image_with_chinese_path(save_path, cropped)
            # success = cv2.imwrite(save_path, cropped)
            if success:
                # If the save is successful, show a message box indicating the save path
                wx.MessageBox(f"已保存至：{save_path}", "保存成功", wx.OK | wx.ICON_INFORMATION)
            else:
                # If the save fails, show a message box indicating the failure
                wx.MessageBox("保存失败。", "错误", wx.OK | wx.ICON_ERROR)


if __name__ == "__main__":
    app = wx.App(False)
    frame = IDCardCropApp()
    app.MainLoop()
