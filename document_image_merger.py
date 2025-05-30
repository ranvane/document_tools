import wx
import os
from PIL import Image

DPI = 300

def mm_to_pixel(mm):
    return int(round(mm * DPI / 25.4))

A4_SIZE_MM = (210, 297)
A4_SIZE_PX = (mm_to_pixel(A4_SIZE_MM[0]), mm_to_pixel(A4_SIZE_MM[1]))

class ImageViewPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.image_paths = []

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 显示文件名列表
        self.listbox = wx.ListBox(self, style=wx.LB_EXTENDED)
        main_sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 5)

        # 按钮区：清除全部 & 删除选中
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clear_btn = wx.Button(self, label="清除全部")
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_sizer.Add(clear_btn)

        delete_btn = wx.Button(self, label="删除选中")
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete_selected)
        btn_sizer.Add(delete_btn, flag=wx.LEFT, border=5)

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(main_sizer)

        # 支持拖拽添加图片文件
        drop_target = DropTarget(self)
        self.SetDropTarget(drop_target)

    def add_images(self, paths):
        for path in paths:
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')) and path not in self.image_paths:
                self.image_paths.append(path)
                self.listbox.Append(os.path.basename(path))

    def clear(self):
        self.image_paths.clear()
        self.listbox.Clear()

    def on_clear(self, event):
        self.clear()

    def on_delete_selected(self, event):
        selections = self.listbox.GetSelections()
        for index in reversed(selections):  # 从后往前删，避免索引错乱
            del self.image_paths[index]
            self.listbox.Delete(index)

class PreviewPanel(wx.ScrolledWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.bitmap_controls = []
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetScrollRate(5, 5)
        self.EnableScrolling(True, True)

    def show_preview(self, pages):
        for ctrl in self.bitmap_controls:
            ctrl.Destroy()
        self.bitmap_controls.clear()
        self.sizer.Clear()

        max_width = 0
        total_height = 0

        for page in pages:
            width, height = page.size
            scale = min(600 / width, 1)
            new_size = (int(width * scale), int(height * scale))
            resized_page = page.resize(new_size, Image.LANCZOS)
            wx_img = wx.Image(resized_page.width, resized_page.height)
            wx_img.SetData(resized_page.convert("RGB").tobytes())

            bmp = wx.StaticBitmap(self, -1, wx.Bitmap(wx_img))
            self.sizer.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.bitmap_controls.append(bmp)

            if new_size[0] > max_width:
                max_width = new_size[0]
            total_height += new_size[1]

        self.SetVirtualSize((max_width, total_height))
        self.Layout()

class DropTarget(wx.FileDropTarget):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel

    def OnDropFiles(self, x, y, filenames):
        self.panel.add_images(filenames)
        return True

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="证件图片合并器 - 带预览", size=(1200, 800))
        self.Center()
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        left_panel = wx.Panel(panel)
        right_panel = wx.Panel(panel)

        left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.image_panel = ImageViewPanel(left_panel)
        self.image_panel.SetBackgroundColour("light gray")

        file_btn = wx.Button(left_panel, label="选择图片")
        file_btn.Bind(wx.EVT_BUTTON, self.on_choose_files)

        preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.preset_choice = wx.Choice(left_panel, choices=["户口本 (105mm)", "身份证 (85.6mm)", "自定义"])
        self.width_input = wx.TextCtrl(left_panel, value="100")
        self.unit_choice = wx.Choice(left_panel, choices=["mm", "pixel"])
        preset_sizer.Add(wx.StaticText(left_panel, label="目标宽度："), flag=wx.ALIGN_CENTER)
        preset_sizer.Add(self.preset_choice, flag=wx.LEFT | wx.RIGHT, border=5)
        preset_sizer.Add(self.width_input, flag=wx.LEFT | wx.RIGHT, border=5)
        preset_sizer.Add(self.unit_choice)

        self.preset_choice.SetSelection(1)
        self.on_preset_change(None)
        self.preset_choice.Bind(wx.EVT_CHOICE, self.on_preset_change)

        gap_sizer = wx.BoxSizer(wx.HORIZONTAL)
        gap_sizer.Add(wx.StaticText(left_panel, label="图片间距："), flag=wx.ALIGN_CENTER_VERTICAL)
        self.gap_input = wx.TextCtrl(left_panel, value="25")  # 默认25mm
        self.gap_unit_choice = wx.Choice(left_panel, choices=["mm", "pixel"])
        self.gap_unit_choice.SetSelection(0)
        gap_sizer.Add(self.gap_input, flag=wx.LEFT | wx.RIGHT, border=5)
        gap_sizer.Add(self.gap_unit_choice)

        merge_btn = wx.Button(left_panel, label="开始合并")
        merge_btn.Bind(wx.EVT_BUTTON, self.on_merge)

        save_btn = wx.Button(left_panel, label="另存为图片")
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(merge_btn, flag=wx.ALL, border=5)
        button_sizer.Add(save_btn, flag=wx.ALL, border=5)

        left_sizer.Add(file_btn, flag=wx.ALL, border=5)
        left_sizer.Add(self.image_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        left_sizer.Add(preset_sizer, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        left_sizer.Add(gap_sizer, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        left_sizer.Add(button_sizer, flag=wx.ALL, border=5)

        left_panel.SetSizer(left_sizer)

        self.preview_panel = PreviewPanel(right_panel)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer.Add(self.preview_panel, 1, wx.EXPAND | wx.ALL, 10)
        right_panel.SetSizer(right_sizer)

        main_sizer.Add(left_panel, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(right_panel, 2, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(main_sizer)

        self.merged_pages = []

    def on_choose_files(self, event):
        wildcard = "Image files (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg"
        dialog = wx.FileDialog(self, "选择图片文件", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            self.image_panel.add_images(paths)
        dialog.Destroy()

    def on_preset_change(self, event):
        index = self.preset_choice.GetSelection()
        if index == 0:
            self.width_input.SetValue("105")
            self.unit_choice.SetSelection(0)
            self.width_input.Enable(False)
            self.unit_choice.Enable(False)
        elif index == 1:
            self.width_input.SetValue("85.6")
            self.unit_choice.SetSelection(0)
            self.width_input.Enable(False)
            self.unit_choice.Enable(False)
        else:
            self.width_input.Enable(True)
            self.unit_choice.Enable(True)

    def on_merge(self, event):
        if not self.image_panel.image_paths:
            wx.MessageBox("请先拖入或选择图片！", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        try:
            target_width = float(self.width_input.GetValue())
        except ValueError:
            wx.MessageBox("请输入有效的宽度数值。", "错误", wx.OK | wx.ICON_ERROR)
            return

        unit = 'mm' if self.unit_choice.GetSelection() == 0 else 'px'
        target_width_px = mm_to_pixel(target_width) if unit == 'mm' else int(target_width)

        try:
            gap_value = float(self.gap_input.GetValue())
        except ValueError:
            wx.MessageBox("请输入有效的图片间距数值。", "错误", wx.OK | wx.ICON_ERROR)
            return

        gap_unit = 'mm' if self.gap_unit_choice.GetSelection() == 0 else 'px'
        gap_height = mm_to_pixel(gap_value) if gap_unit == 'mm' else int(gap_value)

        pages = []
        current_page = Image.new('RGB', A4_SIZE_PX, color='white')
        draw_y = 0
        items = []

        for path in self.image_panel.image_paths:
            with Image.open(path) as img:
                # 计算缩放比例和新尺寸
                index = self.preset_choice.GetSelection()
                if index == 0:  # 户口本模式
                    target_height_px = mm_to_pixel(148/2)  # 户口本标准高度148mm,这里使用单页 模式
                    ratio = target_height_px / img.height
                    new_size = (int(img.width * ratio), target_height_px)
                    resized_img = img.resize(new_size, Image.LANCZOS)
                elif index == 1:  # 身份证模式
                    target_height_px = mm_to_pixel(54)  # 身份证标准高度54mm
                    ratio = target_height_px / img.height
                    new_size = (int(img.width * ratio), target_height_px)
                    resized_img = img.resize(new_size, Image.LANCZOS)
                else:  # 自定义模式
                    ratio = target_width_px / img.width
                    new_size = (target_width_px, int(img.height * ratio))
                    resized_img = img.resize(new_size, Image.LANCZOS)

                if draw_y + resized_img.height > A4_SIZE_PX[1]:
                    y_offset = (A4_SIZE_PX[1] - draw_y + gap_height) // 2
                    for img_obj, h in items:
                        x = (A4_SIZE_PX[0] - img_obj.width) // 2
                        current_page.paste(img_obj, (x, y_offset))
                        y_offset += h + gap_height
                    pages.append(current_page)
                    current_page = Image.new('RGB', A4_SIZE_PX, color='white')
                    draw_y = 0
                    items.clear()

                items.append((resized_img, resized_img.height))
                draw_y += resized_img.height + gap_height

        if items:
            y_offset = (A4_SIZE_PX[1] - draw_y + gap_height) // 2
            for img_obj, h in items:
                x = (A4_SIZE_PX[0] - img_obj.width) // 2
                current_page.paste(img_obj, (x, y_offset))
                y_offset += h + gap_height
            pages.append(current_page)

        self.preview_panel.show_preview(pages)
        self.merged_pages = pages
        # wx.MessageBox("合并完成，请点击【另存为图片】保存文件。", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_save(self, event):
        if not self.merged_pages:
            wx.MessageBox("没有可保存的合并内容，请先进行合并。", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        dialog = wx.FileDialog(self, "另存为", wildcard="PNG 文件 (*.png)|*.png|JPG 文件 (*.jpg)|*.jpg",
                                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg']:
                save_path = path
                format_type = "PNG" if ext == ".png" else "JPEG"
            else:
                save_path = path + ".png"
                format_type = "PNG"

            self.merged_pages[0].save(save_path, format=format_type)
            wx.MessageBox(f"保存成功：{save_path}", "提示", wx.OK | wx.ICON_INFORMATION)
        dialog.Destroy()

if __name__ == "__main__":
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
