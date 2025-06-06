import wx
import os
from PIL import Image,ImageEnhance
from loguru import logger
import cv2
import numpy as np

DPI = 300

def mm_to_pixel(mm):
    return int(round(mm * DPI / 25.4))

A4_SIZE_MM = (210, 297)
A4_SIZE_PX = (mm_to_pixel(A4_SIZE_MM[0]), mm_to_pixel(A4_SIZE_MM[1]))

# 预设证件尺寸（单位：毫米）适当加大
ID_CARD_SIZE_MM = (86, 54)     # 身份证（85.6毫米 ×54毫米）
HUKOU_SIZE_MM = (145, 106)        # 户口本（143 毫米 ×105 毫米）
STUDENT_CARD_SIZE_MM = (120, 90)  # 学生证
# 预先转换成像素
ID_CARD_SIZE_PX = (mm_to_pixel(ID_CARD_SIZE_MM[0]), mm_to_pixel(ID_CARD_SIZE_MM[1]))
HUKOU_SIZE_PX = (mm_to_pixel(HUKOU_SIZE_MM[0]), mm_to_pixel(HUKOU_SIZE_MM[1]))
STUDENT_CARD_SIZE_PX = (mm_to_pixel(STUDENT_CARD_SIZE_MM[0]), mm_to_pixel(STUDENT_CARD_SIZE_MM[1]))

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
        super().__init__(None, title="证件图片合并器", size=(1200, 800))
        # 加载图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "document_merger_icon.ico")
            if os.path.exists(icon_path):
                icon = wx.Icon(icon_path, wx.BITMAP_TYPE_ICO)
                self.SetIcon(icon)
        except Exception as e:
            logger.error(f"Failed to load icon: {e}")
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
        # -----------------------------
        # 预设和宽度设置行
        preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.preset_choice = wx.Choice(left_panel,
                                       choices=["户口本 (148mm)", "身份证 (85.6mm)", "学生证 (120mm)", "自定义"])
        self.width_input = wx.TextCtrl(left_panel, value="100")
        self.unit_choice = wx.Choice(left_panel, choices=["mm", "pixel"])
        self.unit_choice.SetSelection(0)

        preset_sizer.Add(wx.StaticText(left_panel, label="目标宽度："), flag=wx.ALIGN_CENTER)
        preset_sizer.Add(self.preset_choice, flag=wx.LEFT | wx.RIGHT, border=5)
        preset_sizer.Add(self.width_input, flag=wx.LEFT | wx.RIGHT, border=5)
        preset_sizer.Add(self.unit_choice, flag=wx.LEFT | wx.RIGHT, border=5)

        # 漂白相关控件 - 新增一行
        bleach_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bleach_checkbox = wx.CheckBox(left_panel, label="漂白图片")
        self.bleach_stage_choice = wx.Choice(left_panel, choices=["黑白", "背景去除", "优化"])
        self.bleach_stage_choice.SetSelection(0)
        self.bleach_stage_choice.Enabled  = False
        # 绑定事件
        self.bleach_checkbox.Bind(wx.EVT_CHECKBOX, self.on_bleach_checkbox)

        self.preset_choice.SetSelection(1)
        self.on_preset_change(None)
        self.preset_choice.Bind(wx.EVT_CHOICE, self.on_preset_change)

        bleach_sizer.Add(wx.StaticText(left_panel, label="图片间距："), flag=wx.ALIGN_CENTER_VERTICAL)
        self.gap_input = wx.TextCtrl(left_panel, value="15")  # 默认15mm
        self.gap_unit_choice = wx.Choice(left_panel, choices=["mm", "pixel"])
        self.gap_unit_choice.SetSelection(0)
        #  添加间距控件
        bleach_sizer.Add(self.gap_input,  flag=wx.ALIGN_CENTER_VERTICAL, border=5)
        bleach_sizer.Add(self.gap_unit_choice, flag=wx.ALIGN_CENTER_VERTICAL, border=5)
        #  添加漂白控件
        bleach_sizer.Add(self.bleach_checkbox, flag=wx.ALL, border=5)
        bleach_sizer.Add(self.bleach_stage_choice, flag=wx.ALL, border=5)

        merge_btn = wx.Button(left_panel, label="开始合并")
        merge_btn.Bind(wx.EVT_BUTTON, self.on_merge)

        save_btn = wx.Button(left_panel, label="另存为图片")
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(merge_btn, flag=wx.ALL, border=5)
        button_sizer.Add(save_btn, flag=wx.ALL, border=5)

        left_sizer.Add(file_btn, flag=wx.ALL, border=5)
        left_sizer.Add(self.image_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        # 加入左侧面板布局
        left_sizer.Add(preset_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        left_sizer.Add(bleach_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
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

    def on_bleach_checkbox(self, event):
        """
        处理“漂白图片”复选框状态变化事件。
        根据是否勾选来启用或禁用阶段选择下拉框。
        """
        is_checked = self.bleach_checkbox.GetValue()
        self.bleach_stage_choice.Enable(is_checked)

        # # 可选：如果想在未勾选时重置为默认选项
        # if not is_checked:
        #     self.bleach_stage_choice.SetSelection(0)


    def on_preset_change(self, event):
        """
        处理预设变更事件。
        根据用户选择的不同预设，更改宽度输入框和单位选择框的值和状态，
        以及漂白复选框的选中状态。
        """
        # 获取预设选择框的当前选中项索引
        index = self.preset_choice.GetSelection()
        logger.debug(f"on_preset_change: index={index}")


        # 根据不同的预设索引进行相应的操作
        if index == 0:  # 户口本模式
            # 设置宽度输入框的值为140
            self.width_input.SetValue("140")
            # 设置单位选择框的值为mm
            self.unit_choice.SetSelection(0)
            # 禁用宽度输入框和单位选择框，因为户口本模式下这些值是固定的
            logger.debug(f'index=0')
            self.width_input.Enable(False)
            self.unit_choice.Enable(False)
            # 取消选中漂白复选框
            self.bleach_checkbox.SetValue(False)
        elif index == 1:  # 身份证模式
            # 设置宽度输入框的值为86
            self.width_input.SetValue('85.6')
            # 设置单位选择框的值为mm
            self.unit_choice.SetSelection(0)
            # 禁用宽度输入框和单位选择框，因为身份证模式下这些值是固定的
            logger.debug(f'index=1')
            self.width_input.Enable(False)
            self.unit_choice.Enable(False)
            # 取消选中漂白复选框
            self.bleach_checkbox.SetValue(False)
        elif index == 2:  # 学生证模式
            # 设置宽度输入框的值为120
            self.width_input.SetValue('120')
            # 设置单位选择框的值为mm
            self.unit_choice.SetSelection(0)
            # 禁用宽度输入框和单位选择框，因为学生证模式下这些值是固定的
            logger.debug(f'index=2')
            self.width_input.Enable(False)
            self.unit_choice.Enable(False)
            # 取消选中漂白复选框
            self.bleach_checkbox.SetValue(False)
        elif index == 3:  # 自定义模式
            # 在自定义模式下，将宽度恢复为默认值100
            self.width_input.SetValue("100")
            # 设置默认单位为 "mm"
            self.unit_choice.SetSelection(0)
            # 启用宽度输入框和单位选择框，允许用户进行自定义设置
            self.width_input.Enable(True)
            self.unit_choice.Enable(True)

            # 取消选中漂白复选框
            self.bleach_checkbox.SetValue(False)

        else:  # 身份证、学生证等其他预设模式
            # 启用宽度输入框和单位选择框，但不设置具体的值，由用户决定
            self.width_input.Enable(True)
            self.unit_choice.Enable(True)
            # 取消选中漂白复选框
            self.bleach_checkbox.SetValue(False)

    def bleach_image(self, img, blur_size=5):
        """
        漂白图像，即获取图像的二值化版本

        参数:
            img (PIL.Image): 输入图像
            blur_size (int): 高斯模糊核大小

        返回:
            PIL.Image: 二值化图像
        """
        # 转换为 OpenCV 格式
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 高斯模糊减少噪点
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

        # 自适应阈值处理
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 35, 10)

        # 反转图像（文本为白，背景为黑）
        # binary_inv = cv2.bitwise_not(binary)

        # 转换回 PIL 图像格式
        return Image.fromarray(binary)

    def image_removed_background(self, img, bg_strength=0.8, blur_size=5):
        """
        获取背景去除后的图像（仅保留前景文本）

        参数:
            img (PIL.Image): 输入图像
            bg_strength (float): 背景去除强度
            blur_size (int): 高斯模糊核大小

        返回:
            PIL.Image: 背景去除后的图像
        """
        # Step 1: 将 PIL 图像转为 OpenCV 格式 (BGR)
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # Step 2: 高斯模糊 + 自适应阈值处理
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 35, 10)
        binary_inv = cv2.bitwise_not(binary)

        # Step 3: 创建背景掩码
        bg_mask = np.ones_like(gray) * 255
        bg_mask[binary_inv > 100] = 0
        bg_mask = cv2.addWeighted(bg_mask, bg_strength, np.zeros_like(bg_mask), 1 - bg_strength, 0)

        # Step 4: 应用背景掩码
        img_with_bg_removed = img_cv.copy()
        img_with_bg_removed[bg_mask > 100] = [255, 255, 255]

        # Step 5: 转换回 PIL 图像格式
        return Image.fromarray(cv2.cvtColor(img_with_bg_removed, cv2.COLOR_BGR2RGB))

    def enhanced_image(self, img, bg_strength=0.8, text_strength=1.2, gray_preservation=0.6, blur_size=5):
        """
        获取最终增强后的图像（结合对比度增强和灰度保留）

        参数:
            img (PIL.Image): 输入图像
            bg_strength (float): 背景去除强度
            text_strength (float): 文本增强强度
            gray_preservation (float): 灰度保留程度
            blur_size (int): 高斯模糊核大小

        返回:
            PIL.Image: 增强后的图像
        """
        # Step 1: 背景去除
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 35, 10)
        binary_inv = cv2.bitwise_not(binary)

        # Step 2: 创建背景掩码
        bg_mask = np.ones_like(gray) * 255
        bg_mask[binary_inv > 100] = 0
        bg_mask = cv2.addWeighted(bg_mask, bg_strength, np.zeros_like(bg_mask), 1 - bg_strength, 0)

        # Step 3: 应用背景掩码
        img_with_bg_removed = img_cv.copy()
        img_with_bg_removed[bg_mask > 100] = [255, 255, 255]

        # Step 4: 对比度增强
        img_pil = Image.fromarray(cv2.cvtColor(img_with_bg_removed, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(img_pil)
        enhanced_img = enhancer.enhance(text_strength)
        enhanced_cv = cv2.cvtColor(np.array(enhanced_img), cv2.COLOR_RGB2BGR)

        # Step 5: 保留灰度层次
        result = cv2.addWeighted(enhanced_cv, gray_preservation, img_cv, 1 - gray_preservation, 0)

        # Step 6: 转换回 PIL 图像格式
        return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

    def on_merge(self, event):
        """
        处理图片合并事件。

        此函数负责将用户选择的多张图片按照指定的宽度和间距合并成一页或多页A4大小的图片。
        合并后的图片显示在预览面板，用户可以选择保存。

        参数:
        - event: 触发的事件对象，通常由界面操作产生。

        返回值:
        无
        """
        # 检查是否有图片需要合并
        if not self.image_panel.image_paths:
            wx.MessageBox("请先拖入或选择图片！", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        # 获取目标宽度并进行有效性检查
        try:
            target_width = float(self.width_input.GetValue())
        except ValueError:
            wx.MessageBox("请输入有效的宽度数值。", "错误", wx.OK | wx.ICON_ERROR)
            return

        # 根据用户选择的单位处理目标宽度
        unit = 'mm' if self.unit_choice.GetSelection() == 0 else 'px'
        target_width_px = mm_to_pixel(target_width) if unit == 'mm' else int(target_width)

        # 获取图片间距并进行有效性检查
        try:
            gap_value = float(self.gap_input.GetValue())
        except ValueError:
            wx.MessageBox("请输入有效的图片间距数值。", "错误", wx.OK | wx.ICON_ERROR)
            return

        # 根据用户选择的单位处理图片间距
        gap_unit = 'mm' if self.gap_unit_choice.GetSelection() == 0 else 'px'
        gap_height = mm_to_pixel(gap_value) if gap_unit == 'mm' else int(gap_value)

        # 初始化页面和当前绘制位置
        pages = []
        current_page = Image.new('RGB', A4_SIZE_PX, color='white')
        draw_y = 0
        items = []

        # 遍历所有图片并根据用户选择的模式进行处理
        for path in self.image_panel.image_paths:
            with Image.open(path) as img:
                # 计算缩放比例和新尺寸
                index = self.preset_choice.GetSelection()#获取用户选择的预设模式
                if index == 0:  # 户口本模式
                    target_size = HUKOU_SIZE_PX
                elif index == 1:  # 身份证模式
                    target_size = ID_CARD_SIZE_PX
                elif index == 2:  # 学生证模式
                    target_size = STUDENT_CARD_SIZE_PX
                else:  # 自定义模式
                    ratio = target_width_px / img.width
                    target_size = (target_width_px, int(img.height * ratio))

                resized_img = img.resize(target_size, Image.LANCZOS)# 缩放图片，并使用LANCZOS算法进行平滑插值

                # 根据复选框状态进行漂白处理
                if self.bleach_checkbox.GetValue():
                    stage_index = self.bleach_stage_choice.GetSelection()

                    if stage_index == 0:  # 二值化
                        resized_img = self.bleach_image(resized_img)
                    elif stage_index == 1:  # 背景去除
                        resized_img = self.image_removed_background(resized_img)
                    elif stage_index == 2:  # 优化
                        resized_img = self.enhanced_image(resized_img)


                # 检查当前页面是否需要翻页
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

                # 将调整后的图片添加到当前页面的绘制列表中
                items.append((resized_img, resized_img.height))
                draw_y += resized_img.height + gap_height

        # 处理最后一页的绘制
        if items:
            y_offset = (A4_SIZE_PX[1] - draw_y + gap_height) // 2
            for img_obj, h in items:
                x = (A4_SIZE_PX[0] - img_obj.width) // 2
                current_page.paste(img_obj, (x, y_offset))
                y_offset += h + gap_height
            pages.append(current_page)

        # 显示合并后的预览并保存结果
        self.preview_panel.show_preview(pages)
        self.merged_pages = pages
        # wx.MessageBox("合并完成，请点击【另存为图片】保存文件。", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_save(self, event):
        if not self.merged_pages:
            wx.MessageBox("没有可保存的合并内容，请先进行合并。", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        # 获取第一个图片文件的目录作为默认保存路径
        default_path = ""
        if self.image_panel.image_paths:
            default_path = os.path.dirname(self.image_panel.image_paths[0])

        dialog = wx.FileDialog(
            self,
            "另存为",
            defaultDir=default_path,  # 设置默认目录
            wildcard="JPG 文件 (*.jpg)|*.jpg|PNG 文件 (*.png)|*.png",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.jpg', '.png', '.jpeg']:
                save_path = path
                format_type = "JPEG" if ext in ('.jpg', '.jpeg') else "PNG"
            else:
                save_path = path + ".jpg"  # 默认改为jpg扩展名
                format_type = "JPEG"

            self.merged_pages[0].save(save_path, format=format_type)
            wx.MessageBox(f"保存成功：{save_path}", "提示", wx.OK | wx.ICON_INFORMATION)
        dialog.Destroy()


if __name__ == "__main__":
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
