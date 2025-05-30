import os
import cv2
import wx


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
        self.image_path = path
        self.orig_image = cv2.imread(path)
        if self.orig_image is None:
            wx.MessageBox("无法加载图像。请确认文件格式正确。", "错误", wx.OK | wx.ICON_ERROR)
            return
        self.detect_and_show_crops()
        self.crop_btn.Enable()
        self.saveas_btn.Enable()

    def detect_and_show_crops(self):
        image = self.orig_image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.crops = []

        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4 and cv2.contourArea(cnt) > 5000:
                x, y, w, h = cv2.boundingRect(cnt)
                self.crops.append((x, y, w, h))

        if self.crops:
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
        if not self.crops:
            return
        x, y, w, h = self.crops[self.selected_crop_idx]
        cropped = self.orig_image[y:y + h, x:x + w]
        cv2.imwrite(self.image_path, cropped)
        wx.MessageBox("裁剪区域已保存并覆盖原图。", "保存成功", wx.OK | wx.ICON_INFORMATION)

        # ... existing code ...

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
            success = cv2.imwrite(save_path, cropped)
            if success:
                # If the save is successful, show a message box indicating the save path
                wx.MessageBox(f"已保存至：{save_path}", "保存成功", wx.OK | wx.ICON_INFORMATION)
            else:
                # If the save fails, show a message box indicating the failure
                wx.MessageBox("保存失败。", "错误", wx.OK | wx.ICON_ERROR)

    # ... existing code ...


if __name__ == "__main__":
    app = wx.App(False)
    frame = IDCardCropApp()
    app.MainLoop()
