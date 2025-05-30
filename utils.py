import cv2
import numpy as np
from loguru import logger


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
    except Exception as e:
        logger.error(f"图像预处理出错: {e}")
        return None, None


def detect_edges(blurred):
    """
    边缘检测：使用自适应 Canny 算法提取图像边缘

    Args:
        blurred (numpy.ndarray): 经过模糊处理后的图像

    Returns:
        numpy.ndarray: 经过边缘检测和形态学膨胀操作后的图像
    """
    try:
        # 检查输入是否为有效的 numpy 数组
        if not isinstance(blurred, np.ndarray):
            raise TypeError("输入必须是 numpy.ndarray 类型的图像")
        if blurred.ndim not in [2]:
            raise ValueError("输入图像维度必须是 2")

        # 计算图像的中位数，用于后续自适应阈值的计算
        median = np.median(blurred)

        # 依据中位数计算 Canny 边缘检测的高低阈值
        # 下限阈值为中位数的 67%，且不小于 0
        lower = int(max(0, (1.0 - 0.33) * median))
        # 上限阈值为中位数的 133%，且不大于 255
        upper = int(min(255, (1.0 + 0.33) * median))

        # 使用计算得到的自适应阈值进行 Canny 边缘检测
        edges = cv2.Canny(blurred, lower, upper)

        # 定义一个 3x3 的结构元素，用于形态学膨胀操作
        kernel = np.ones((3, 3), np.uint8)
        # 对边缘图像进行形态学膨胀操作，连接断开的边缘
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        return dilated_edges
    except Exception as e:
        logger.error(f"边缘检测出错: {e}")
        return None


def find_document_contour(edges, original_img):
    """
    轮廓检测与筛选：找到最可能的纸张轮廓

    参数:
        edges (numpy.ndarray): 经过边缘检测后的图像，包含图像的边缘信息
        original_img (numpy.ndarray): 原始输入图像，用于复制操作，不在其上绘制轮廓

    返回:
        numpy.ndarray: 最可能的纸张轮廓，如果未找到则为 None
    """
    try:
        # 检查输入是否为有效的 numpy 数组
        if not isinstance(edges, np.ndarray):
            raise TypeError("edges 必须是 numpy.ndarray 类型的图像")
        if not isinstance(original_img, np.ndarray):
            raise TypeError("original_img 必须是 numpy.ndarray 类型的图像")

        # 检查图像维度
        if edges.ndim != 2:
            raise ValueError("edges 图像维度必须是 2")
        if original_img.ndim not in [2, 3]:
            raise ValueError("original_img 图像维度必须是 2 或 3")

        # 查找轮廓
        # 使用 cv2.findContours 函数在边缘图像中查找外部轮廓
        # cv2.RETR_EXTERNAL 表示只检测外部轮廓
        # cv2.CHAIN_APPROX_SIMPLE 表示压缩水平、垂直和对角方向的冗余点
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        # 按面积降序排序轮廓，面积大的轮廓排在前面
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # 初始化文档轮廓为 None，表示尚未找到合适的轮廓
        document_contour = None
        # 复制原始图像，避免在原始图像上直接操作
        img_with_contours = original_img.copy()

        # 自适应计算面积阈值，根据图像大小调整
        # 获取原始图像的高度和宽度
        height, width = original_img.shape[:2]
        # 最小面积阈值设置为图像总面积的 1%，可根据实际情况调整比例
        min_area_threshold = 0.01 * height * width

        # 遍历轮廓，筛选最可能的纸张轮廓
        for contour in contours:
            # 计算当前轮廓的面积
            area = cv2.contourArea(contour)
            # 如果轮廓面积小于最小面积阈值，则跳过该轮廓
            if area < min_area_threshold:
                continue

            # 自适应计算多边形近似精度，根据轮廓周长调整
            # 多边形近似精度设置为轮廓周长的 2%
            epsilon = 0.02 * cv2.arcLength(contour, True)
            # 使用多边形逼近方法对轮廓进行近似，减少轮廓的点数
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # 筛选条件：轮廓为四边形，且面积足够大
            if len(approx) == 4:
                # 找到符合条件的四边形轮廓，将其作为文档轮廓
                document_contour = approx
                break

        # 返回找到的轮廓（若存在）
        return document_contour
    except Exception as e:
        logger.error(f"查找文档轮廓时出错: {e}")
        return None


def draw_boxes_on_image(frame, boxes, color=(0, 255, 0), thickness=5):
    """
    在图像上绘制多个方框
    参数:
        frame (numpy.ndarray): 输入图像
        boxes (list): 包含多个方框的列表，每个方框由四个点的坐标组成
        color (tuple): 方框的颜色，默认为绿色 (0, 255, 0)
        thickness (int): 方框的线宽，默认为 5
    返回:
        numpy.ndarray: 带有绘制方框的图像
    """
    try:

        # 检查输入的 boxes 是否为列表
        if not isinstance(boxes, list):
            logger.error("输入的 boxes 必须是列表类型")

        # 检查 color 是否为有效的元组
        if not isinstance(color, tuple) or len(color) != 3:
            logger.error("color 必须是长度为 3 的元组")

        # 检查 thickness 是否为正整数
        if not isinstance(thickness, int) or thickness <= 0:
            logger.error("thickness 必须是正整数")

        img_with_boxes = frame.copy()
        for box in boxes:
            # 检查每个方框是否为有效的 numpy 数组
            if not isinstance(box, np.ndarray):
                box = np.array(box, dtype=np.int32)
            if box.ndim != 2 or box.shape[1] != 2:
                logger.error("每个方框必须是二维数组，且第二维长度为 2")
            cv2.drawContours(img_with_boxes, [box], -1, color, thickness)

        return img_with_boxes
    except Exception as e:
        logger.error(f"在图像上绘制方框时出错: {e}")
        return frame


def detect_contour(frame):
    """
    检测图像中的方框并绘制面积最大的边界框
    :param frame: 输入图像帧
    :return: 最可能的文档轮廓和带有边界框的图像帧
    """
    try:
        # 检查输入的 frame 是否为有效的 numpy 数组
        if not isinstance(frame, np.ndarray):
            logger.error("输入的 frame 必须是 numpy.ndarray 类型的图像")
        if frame.ndim not in [2, 3]:
            logger.error("输入图像维度必须是 2 或 3")

        # 1. 图像预处理
        _, blurred = preprocess_image(frame)
        if blurred is None:
            logger.error("图像预处理失败，无法进行后续操作")
            return None, frame

        # 2. 边缘检测
        edged = detect_edges(blurred)
        if edged is None:
            logger.error("边缘检测失败，无法进行后续操作")
            return None, frame

        # 3. 轮廓检测与筛选
        document_contour = find_document_contour(edged, frame)

        # 绘制边界框
        if document_contour is not None:
            frame = draw_boxes_on_image(frame, [document_contour])
        return document_contour, frame
    except Exception as e:
        logger.error(f"检测轮廓时出错: {e}")
        return None, frame


def order_points(pts):
    """
    对四个点进行排序：左上，右上，右下，左下

    参数:
        pts (numpy.ndarray): 输入的四个点的坐标

    返回:
        rect (numpy.ndarray): 排序后的四个点的坐标

    异常:
        TypeError: 当 pts 不是 numpy.ndarray 类型时抛出
        ValueError: 当 pts 的维度不是 2 或其形状不是 (4, 2) 时抛出
    """
    try:
        # 检查 pts 的维度和形状
        if pts.ndim != 2 or pts.shape != (4, 2):
            logger.error("输入的 pts 必须是二维数组，且形状为 (4, 2)")

        # 初始化一个形状为 (4, 2) 的零矩阵，数据类型为 float32，用于存储排序后的四个点的坐标
        rect = np.zeros((4, 2), dtype="float32")

        # 计算每个点的 x 坐标和 y 坐标之和，存储在 s 数组中
        # 左上点的 x 和 y 坐标之和通常最小，右下点的 x 和 y 坐标之和通常最大
        s = pts.sum(axis=1)
        # 将和最小的点作为左上点，赋值给 rect 数组的第一个元素
        rect[0] = pts[np.argmin(s)]
        # 将和最大的点作为右下点，赋值给 rect 数组的第三个元素
        rect[2] = pts[np.argmax(s)]

        # 计算每个点的 x 坐标和 y 坐标之差，存储在 diff 数组中
        # 右上点的 x - y 差值通常最小，左下点的 x - y 差值通常最大
        diff = np.diff(pts, axis=1)
        # 将差值最小的点作为右上点，赋值给 rect 数组的第二个元素
        rect[1] = pts[np.argmin(diff)]
        # 将差值最大的点作为左下点，赋值给 rect 数组的第四个元素
        rect[3] = pts[np.argmax(diff)]

        return rect
    except Exception as e:
        logger.error(f"对四个点排序时出错: {e}")
        return None


def four_point_transform(image, pts):
    """
    对图像进行透视变换

    参数:
        image (numpy.ndarray): 输入图像
        pts (numpy.ndarray): 四个点的坐标

    返回:
        warped (numpy.ndarray): 透视变换后的图像

    异常:
        TypeError: 当 image 不是 numpy.ndarray 类型或 pts 不是 numpy.ndarray 类型时抛出
        ValueError: 当 image 维度不正确或 pts 维度不是 2 或其形状不是 (4, 2) 时抛出
    """
    try:
        # 检查 image 是否为有效的 numpy 数组
        if not isinstance(image, np.ndarray):
            logger.error("输入的 image 必须是 numpy.ndarray 类型的图像")
        if image.ndim not in [2, 3]:
            logger.error("输入的 image 维度必须是 2 或 3")

        # 检查 pts 是否为有效的 numpy 数组
        if not isinstance(pts, np.ndarray):
            logger.error("输入的 pts 必须是 numpy.ndarray 类型")
        if pts.ndim != 2 or pts.shape != (4, 2):
            logger.error("输入的 pts 必须是二维数组，且形状为 (4, 2)")

        # 对四个点进行排序：左上，右上，右下，左下
        rect = order_points(pts)
        (tl, tr, br, bl) = rect

        # 计算目标图像的宽度和高度
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = int(max(widthA, widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = int(max(heightA, heightB))

        # 构建目标图像的坐标
        dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1],
                        [0, maxHeight - 1]],
                       dtype="float32")

        # 计算透视变换矩阵并应用
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        return warped
    except Exception as e:
        logger.error(f"进行透视变换时出错: {e}")
        return image


def transform_document(frame):
    """
    扫描文档并进行透视变换

    参数:
        frame (numpy.ndarray): 输入图像

    返回:
        warped (numpy.ndarray): 透视变换后的图像
    """
    try:
        # 检查输入是否为有效的 numpy 数组
        if not isinstance(frame, np.ndarray):
            logger.error("输入的 frame 必须是 numpy.ndarray 类型的图像")
        if frame.ndim not in [2, 3]:
            logger.error("输入图像维度必须是 2 或 3")

        # 1. 图像预处理
        _, blurred = preprocess_image(frame)
        if blurred is None:
            logger.error("图像预处理失败，无法进行后续操作")
            return frame

        # 2. 边缘检测
        edged = detect_edges(blurred)
        if edged is None:
            logger.error("边缘检测失败，无法进行后续操作")
            return frame

        # 3. 轮廓检测与筛选
        document_contour = find_document_contour(edged, frame)

        # 4. 对原始图像进行透视变换（检查是否找到文档轮廓）
        if document_contour is not None:
            # 调整轮廓的形状，使其符合 four_point_transform 函数的输入要求
            pts = document_contour.reshape(4, 2)
            # 对原始图像进行透视变换
            warped = four_point_transform(frame, pts)
        else:
            # 若未找到合适轮廓，返回原始图像
            logger.warning("未找到合适的文档轮廓，返回原始图像")
            warped = frame

        return warped
    except Exception as e:
        logger.error(f"文档透视变换过程中出错: {e}")
        return frame


if __name__ == "__main__":
    # print(count_cameras())
    pass

