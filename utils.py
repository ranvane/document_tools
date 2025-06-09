import cv2
import numpy as np
from loguru import logger
from PIL import Image,ImageEnhance
import time

# 定义一个装饰器，用于计算函数的执行时间
def measure_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        exec_time = end_time - start_time
        print(f"{func.__name__} 执行时间: {exec_time:.4f} 秒")
        return result
    return wrapper

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
    
class SCRFD():
    def __init__(self, onnxmodel, confThreshold=0.5, nmsThreshold=0.5):
        """
        初始化 SCRFD 类的实例。

        :param onnxmodel: ONNX 模型文件的路径
        :param confThreshold: 分类置信度阈值，默认为 0.5
        :param nmsThreshold: 非极大值抑制（NMS）的 IoU 阈值，默认为 0.5
        """
        # 输入图像的宽度
        self.inpWidth = 640
        # 输入图像的高度
        self.inpHeight = 640
        # 分类置信度阈值，用于过滤低置信度的检测结果
        self.confThreshold = confThreshold
        # 非极大值抑制的 IoU 阈值，用于去除重叠的检测框
        self.nmsThreshold = nmsThreshold
        # 加载 ONNX 模型
        self.net = cv2.dnn.readNet(onnxmodel)
        # 是否保持图像的宽高比，默认为 True
        self.keep_ratio = True
        # 特征金字塔网络（FPN）的特征图数量
        self.fmc = 3
        # FPN 各层的特征步长
        self._feat_stride_fpn = [8, 16, 32]
        # 每个位置的锚框数量
        self._num_anchors = 4

    def resize_image(self, srcimg):
        """
        调整输入图像的大小，根据是否保持宽高比进行不同处理，并在需要时添加边框。

        :param srcimg: 输入的原始图像
        :return: 调整大小后的图像，以及新的高度、宽度和上下左右的填充量
        """
        # 初始化填充量和新的高度、宽度
        padh, padw, newh, neww = 0, 0, self.inpHeight, self.inpWidth
        # 检查是否需要保持宽高比且图像的高度和宽度不相等
        if self.keep_ratio and srcimg.shape[0] != srcimg.shape[1]:
            # 计算图像的高宽比
            hw_scale = srcimg.shape[0] / srcimg.shape[1]
            if hw_scale > 1:
                # 高度大于宽度，调整宽度以保持宽高比
                newh, neww = self.inpHeight, int(self.inpWidth / hw_scale)
                # 调整图像大小
                img = cv2.resize(srcimg, (neww, newh), interpolation=cv2.INTER_AREA)
                # 计算左右填充量
                padw = int((self.inpWidth - neww) * 0.5)
                # 添加左右边框
                img = cv2.copyMakeBorder(img, 0, 0, padw, self.inpWidth - neww - padw, cv2.BORDER_CONSTANT,
                                         value=0)  
            else:
                # 宽度大于高度，调整高度以保持宽高比
                newh, neww = int(self.inpHeight * hw_scale) + 1, self.inpWidth
                # 调整图像大小
                img = cv2.resize(srcimg, (neww, newh), interpolation=cv2.INTER_AREA)
                # 计算上下填充量
                padh = int((self.inpHeight - newh) * 0.5)
                # 添加上下边框
                img = cv2.copyMakeBorder(img, padh, self.inpHeight - newh - padh, 0, 0, cv2.BORDER_CONSTANT, value=0)
        else:
            # 不保持宽高比，直接调整图像到指定大小
            img = cv2.resize(srcimg, (self.inpWidth, self.inpHeight), interpolation=cv2.INTER_AREA)
        return img, newh, neww, padh, padw
    def distance2bbox(self, points, distance, max_shape=None):
        """
        根据中心点坐标和偏移量计算边界框的坐标。

        :param points: 中心点坐标数组，形状为 (N, 2)，N 为点的数量，每个点包含 (x, y) 坐标
        :param distance: 偏移量数组，形状为 (N, 4)，每个点的偏移量依次为 (left, top, right, bottom)
        :param max_shape: 可选参数，图像的最大形状 (height, width)，用于限制边界框坐标在图像范围内
        :return: 边界框坐标数组，形状为 (N, 4)，每个边界框包含 (x1, y1, x2, y2) 坐标
        """
        # 计算边界框左上角的 x 坐标，通过中心点 x 坐标减去左偏移量
        x1 = points[:, 0] - distance[:, 0]
        # 计算边界框左上角的 y 坐标，通过中心点 y 坐标减去上偏移量
        y1 = points[:, 1] - distance[:, 1]
        # 计算边界框右下角的 x 坐标，通过中心点 x 坐标加上右偏移量
        x2 = points[:, 0] + distance[:, 2]
        # 计算边界框右下角的 y 坐标，通过中心点 y 坐标加上下偏移量
        y2 = points[:, 1] + distance[:, 3]
        # 如果提供了图像的最大形状，则对边界框坐标进行裁剪，确保坐标在图像范围内
        if max_shape is not None:
            # 限制 x1 坐标在 [0, max_shape[1]] 范围内
            x1 = np.clip(x1, 0, max_shape[1])
            # 限制 y1 坐标在 [0, max_shape[0]] 范围内
            y1 = np.clip(y1, 0, max_shape[0])
            # 限制 x2 坐标在 [0, max_shape[1]] 范围内
            x2 = np.clip(x2, 0, max_shape[1])
            # 限制 y2 坐标在 [0, max_shape[0]] 范围内
            y2 = np.clip(y2, 0, max_shape[0])
        # 将计算得到的边界框坐标按列堆叠成一个数组返回
        return np.stack([x1, y1, x2, y2], axis=-1)
    def distance2kps(self, points, distance, max_shape=None):
        """
        根据中心点坐标和偏移量计算关键点的坐标。

        :param points: 中心点坐标数组，形状为 (N, 2)，N 为点的数量，每个点包含 (x, y) 坐标
        :param distance: 偏移量数组，形状为 (N, M)，M 是关键点偏移量的总数，每两个值对应一个关键点的 (x, y) 偏移量
        :param max_shape: 可选参数，图像的最大形状 (height, width)，用于限制关键点坐标在图像范围内
        :return: 关键点坐标数组，形状为 (N, M//2, 2)
        """
        # 存储关键点坐标的列表
        preds = []
        # 遍历偏移量数组，每两个值为一组，代表一个关键点的 (x, y) 偏移量
        for i in range(0, distance.shape[1], 2):
            # 计算关键点的 x 坐标，通过中心点 x 坐标加上对应的 x 偏移量
            px = points[:, i % 2] + distance[:, i]
            # 计算关键点的 y 坐标，通过中心点 y 坐标加上对应的 y 偏移量
            py = points[:, i % 2 + 1] + distance[:, i + 1]
            # 如果提供了图像的最大形状，则对关键点坐标进行裁剪，确保坐标在图像范围内
            if max_shape is not None:
                # 注意：原代码使用了 PyTorch 的 clamp 方法，这里修正为 NumPy 的 clip 方法
                px = np.clip(px, 0, max_shape[1])
                py = np.clip(py, 0, max_shape[0])
            # 将计算得到的关键点 x 坐标添加到列表中
            preds.append(px)
            # 将计算得到的关键点 y 坐标添加到列表中
            preds.append(py)
        # 将关键点坐标列表按列堆叠成一个数组返回
        return np.stack(preds, axis=-1)
    
    @measure_time
    def detect(self, srcimg):
        """
        对输入图像进行目标检测，返回绘制后的图片和检测目标四个角点的坐标。

        :param srcimg: 输入的原始图像
        :return: 包含绘制后的图片和检测目标四个角点坐标列表的列表，格式为 [outimg, corner_points_list]
        """
        # 调整输入图像的大小，并获取调整后的图像信息和填充量
        img, newh, neww, padh, padw = self.resize_image(srcimg)
        # 将调整后的图像转换为适合网络输入的 blob 格式
        blob = cv2.dnn.blobFromImage(img, 1.0 / 128, (self.inpWidth, self.inpHeight), (127.5, 127.5, 127.5), swapRB=True)
        # 将 blob 数据设置为网络的输入
        self.net.setInput(blob)

        # 执行前向传播，获取网络输出层的输出结果
        outs = self.net.forward(self.net.getUnconnectedOutLayersNames())
        
        # 初始化存储得分、边界框和关键点的列表
        scores_list, bboxes_list, kpss_list = [], [], []
        # 遍历特征金字塔网络（FPN）各层的特征步长
        for idx, stride in enumerate(self._feat_stride_fpn):
            # 获取当前层的分类得分
            scores = outs[idx * self.fmc][0]
            # 获取当前层的边界框预测结果，并乘以步长进行缩放
            bbox_preds = outs[idx * self.fmc + 1][0] * stride
            # 获取当前层的关键点预测结果，并乘以步长进行缩放
            kps_preds = outs[idx * self.fmc + 2][0] * stride
            # 计算当前层特征图的高度
            height = blob.shape[2] // stride
            # 计算当前层特征图的宽度
            width = blob.shape[3] // stride
            # 生成锚框的中心点坐标
            anchor_centers = np.stack(np.mgrid[:height, :width][::-1], axis=-1).astype(np.float32)
            # 将锚框中心点坐标乘以步长，并调整形状
            anchor_centers = (anchor_centers * stride).reshape((-1, 2))
            # 如果每个位置的锚框数量大于 1，扩展锚框中心点坐标
            if self._num_anchors > 1:
                anchor_centers = np.stack([anchor_centers] * self._num_anchors, axis=1).reshape((-1, 2))

            # 找出得分大于等于置信度阈值的索引
            pos_inds = np.where(scores >= self.confThreshold)[0]
            # 根据锚框中心点和边界框预测结果计算边界框坐标
            bboxes = self.distance2bbox(anchor_centers, bbox_preds)
            # 获取满足条件的得分
            pos_scores = scores[pos_inds]
            # 获取满足条件的边界框
            pos_bboxes = bboxes[pos_inds]
            # 将满足条件的得分添加到列表中
            scores_list.append(pos_scores)
            # 将满足条件的边界框添加到列表中
            bboxes_list.append(pos_bboxes)

            # 根据锚框中心点和关键点预测结果计算关键点坐标
            kpss = self.distance2kps(anchor_centers, kps_preds)
            # 调整关键点坐标的形状
            kpss = kpss.reshape((kpss.shape[0], -1, 2))
            # 获取满足条件的关键点
            pos_kpss = kpss[pos_inds]
            # 将满足条件的关键点添加到列表中
            kpss_list.append(pos_kpss)

        # 将所有得分合并为一维数组
        scores = np.vstack(scores_list).ravel()
        # 将所有边界框合并
        bboxes = np.vstack(bboxes_list)
        # 将所有关键点合并
        kpss = np.vstack(kpss_list)
        # 将边界框的右下角坐标转换为宽高
        bboxes[:, 2:4] = bboxes[:, 2:4] - bboxes[:, 0:2]
        # 计算高度和宽度的缩放比例
        ratioh, ratiow = srcimg.shape[0] / newh, srcimg.shape[1] / neww
        # 将边界框的坐标转换回原始图像的坐标
        bboxes[:, 0] = (bboxes[:, 0] - padw) * ratiow
        bboxes[:, 1] = (bboxes[:, 1] - padh) * ratioh
        bboxes[:, 2] = bboxes[:, 2] * ratiow
        bboxes[:, 3] = bboxes[:, 3] * ratioh
        # 将关键点的坐标转换回原始图像的坐标
        kpss[:, :, 0] = (kpss[:, :, 0] - padw) * ratiow
        kpss[:, :, 1] = (kpss[:, :, 1] - padh) * ratioh
        # 使用非极大值抑制（NMS）过滤重叠的边界框
        indices = cv2.dnn.NMSBoxes(bboxes.tolist(), scores.tolist(), self.confThreshold, self.nmsThreshold)
        # 将 indices 转换为一维数组
        if isinstance(indices, np.ndarray):
            indices = indices.flatten()

        corner_points_list = []
        for i in indices:
            xmin = int(bboxes[i, 0])
            ymin = int(bboxes[i, 1])
            xmax = int(bboxes[i, 0] + bboxes[i, 2])
            ymax = int(bboxes[i, 1] + bboxes[i, 3])

            # 四个角点坐标：左上角、右上角、右下角、左下角
            corner_points = [(xmin, ymin),( xmax, ymin),( xmax, ymax), (xmin, ymax)]
            corner_points_list.append(corner_points)

            # # 在原始图像上绘制边界框
            # cv2.rectangle(srcimg, (xmin, ymin), (xmax, ymax), (0, 0, 255), thickness=2)
            # 遍历每个关键点并在原始图像上绘制
            for j in range(4):
                cv2.circle(srcimg, (int(kpss[i, j, 0]), int(kpss[i, j, 1])), 1, (0,255,0), thickness=-1)
            # 在边界框上方绘制得分
            cv2.putText(srcimg, str(round(scores[i], 3)), (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), thickness=1)
            
            # # 根据角点绘制角点之间的两两连线，不连对角线
            # corner_points = np.array(corner_points, dtype=np.int32)
            # for j in range(len(corner_points)):
            #     start_point = corner_points[j]
            #     end_point = corner_points[(j + 1) % len(corner_points)]
            #     cv2.line(srcimg, tuple(start_point), tuple(end_point), color=(0, 0, 255), thickness=2)

        # 将 BGR 格式转换为 RGB 格式，因为 matplotlib 使用 RGB
        outimg = cv2.cvtColor(srcimg, cv2.COLOR_BGR2RGB)
        return outimg, corner_points_list