import cv2
import numpy as np
from loguru import logger
from PIL import Image,ImageEnhance

def preprocess_image(img):
    """图像预处理：灰度转换、自适应直方图均衡化、自适应高斯模糊去噪"""
    try:
        # 检查输入是否为有效的 numpy 数组
        if not isinstance(img, np.ndarray):
            raise TypeError("输入必须是 numpy.ndarray 类型的图像")
        if img.ndim not in [2, 3]:
            raise ValueError("输入图像维度必须是 2 或 3")

        # 灰度转换
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 自适应直方图均衡化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)

        # 计算图像标准差，自适应调整高斯模糊核大小
        std_dev = np.std(enhanced_gray)
        if std_dev < 20:
            kernel_size = (7, 7)
        elif std_dev < 50:
            kernel_size = (5, 5)
        else:
            kernel_size = (3, 3)

        # 自适应高斯模糊去噪
        blurred = cv2.GaussianBlur(enhanced_gray, kernel_size, 0)
        return enhanced_gray, blurred
    except  Exception as e:
        logger.error(f"处理图片时出错：{e}")
        return img

def bleach_image2(img, blur_size=5):
    """
    漂白图像，即获取图像的二值化版本

    参数:
        img (PIL.Image): 输入图像
        blur_size (int): 高斯模糊核大小

    返回:
        PIL.Image: 二值化图像
    """
    try:
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
    except  Exception as e:
        logger.error(f"处理图片时出错：{e}")
        return img

def bleach_image(img, blur_size=5):
    """
    漂白图像：去除背景灰度、保留文字层次并二值化

    参数:
        img (PIL.Image): 输入图像
        blur_size (int): 高斯模糊核大小（用于去噪）

    返回:
        PIL.Image: 漂白后的二值图像
    """
    try:
        # 转为OpenCV BGR格式
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # 转灰度图
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 使用形态学滤波提取背景
        background = cv2.medianBlur(gray, 21)  # 可尝试 21～31

        # 灰度图减去背景，增强文字
        diff = cv2.absdiff(gray, background)
        diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)

        # 可选模糊以平滑小噪声
        if blur_size > 1:
            diff = cv2.GaussianBlur(diff, (blur_size, blur_size), 0)

        # 使用自适应阈值进行二值化（比固定阈值更适应光照不均场景）
        binary = cv2.adaptiveThreshold(diff, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 35, 15)

        # 反转图像：背景黑、文字白（可根据后续处理需求决定是否反转）
        # binary = cv2.bitwise_not(binary)

        return Image.fromarray(binary)
    except  Exception as e:
        logger.error(f"处理图片时出错：{e}")
        return img
def image_removed_background( img, bg_strength=0.8, blur_size=5):
    """
    获取背景去除后的图像（仅保留前景文本）

    参数:
        img (PIL.Image): 输入图像
        bg_strength (float): 背景去除强度
        blur_size (int): 高斯模糊核大小

    返回:
        PIL.Image: 背景去除后的图像
    """
    try:
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
    except  Exception as e:
        logger.error(f"处理图片时出错：{e}")
        return img
def enhanced_image( img, bg_strength=0.8, text_strength=1.2, gray_preservation=0.6, blur_size=5):
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
    try:
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
    except  Exception as e:
        logger.error(f"处理图片时出错：{e}")
        return img