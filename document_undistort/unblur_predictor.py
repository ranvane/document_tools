import cv2
import numpy as np
import onnxruntime

class NAF_DPM():
    def __init__(self, modelpath):
        """
        初始化 NAF_DPM 类的实例。

        :param modelpath: ONNX 模型文件的路径
        """
        # 创建 ONNX Runtime 会话选项对象
        so = onnxruntime.SessionOptions()
        # 设置日志严重级别为 3，即只显示错误信息
        so.log_severity_level = 3
        # 创建 ONNX Runtime 推理会话
        self.session = onnxruntime.InferenceSession(modelpath, so)
        # 获取模型的输入名称
        self.input_name = self.session.get_inputs()[0].name
    
    def preprocess(self, img):
        """
        对输入图像进行预处理，使其符合模型输入要求。

        :param img: 输入的图像，numpy 数组格式
        :return: 预处理后的图像
        """
        # 归一化操作，将图像像素值从 [0, 255] 缩放到 [0, 1]，并调整通道顺序
        img = img.transpose(2, 0, 1) / 255.0
        # 将图像数据扩展为一个批次的形式，增加一个维度表示批次
        img = np.expand_dims(img, axis=0).astype(np.float32)
        # 转换为模型输入格式
        return img
    
    def predict(self, img):
        """
        使用模型对输入图像进行去模糊预测。

        :param img: 输入的图像，numpy 数组格式
        :return: 去模糊后的图像，numpy 数组格式
        """
        # 对输入图像进行预处理
        img = self.preprocess(img)
        # 运行模型推理，获取预测结果
        pred = self.session.run(None, {self.input_name: img})[0]
        # 对预测结果进行后处理
        out_img = self.postprocess(pred)
        # 将输出图像的数据类型转换为 uint8
        return out_img.astype(np.uint8)
    
    def postprocess(self, img):
        """
        对模型的预测结果进行后处理，将其转换为可显示的图像格式。

        :param img: 模型的预测结果，numpy 数组格式
        :return: 后处理后的图像
        """
        # 去掉批次维度
        img = img[0]
        # 将像素值从 [0, 1] 还原到 [0, 255]，并进行裁剪确保像素值在有效范围内
        img = (img * 255 + 0.5).clip(0, 255).transpose(1, 2, 0)
        return img

class OpenCvBilateral:
    def __init__(self):
        """
        初始化 OpenCvBilateral 类的实例。
        """
        pass

    def predict(self, img):
        """
        使用 OpenCV 的双边滤波、自适应直方图均衡化和锐化滤波器对图像进行处理。

        :param img: 输入的图像，numpy 数组格式
        :return: 处理后的图像
        """
        # 将图像数据类型转换为 uint8
        img = img.astype(np.uint8)
        # 双边滤波，用于平滑图像同时保留边缘信息
        bilateral = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
        # 将图像从 BGR 颜色空间转换为 LAB 颜色空间
        lab = cv2.cvtColor(bilateral, cv2.COLOR_BGR2LAB)
        # 将 LAB 图像分离为 L、a、b 三个通道
        l, a, b = cv2.split(lab)
        # 创建自适应直方图均衡化对象
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        # 对 L 通道进行自适应直方图均衡化
        cl = clahe.apply(l)
        # 将处理后的 L 通道与原始的 a、b 通道合并
        limg = cv2.merge((cl, a, b))
        # 将图像从 LAB 颜色空间转换回 BGR 颜色空间
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 定义锐化滤波器的卷积核
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        # 应用锐化滤波器，增强图像的边缘和细节
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        return sharpened

if __name__=='__main__':
    # 创建 NAF_DPM 模型实例
    model = NAF_DPM('weights/nafdpm.onnx')
    # 创建 OpenCvBilateral 模型实例
    model2 = OpenCvBilateral()
    # 读取输入图像
    img = cv2.imread('images/demo3.jpg')
    # 使用 NAF_DPM 模型对图像进行去模糊处理
    out_img = model.predict(img)
    # 使用 OpenCvBilateral 模型对去模糊后的图像进行进一步处理
    out_img = model2.predict(out_img)
    # 将处理后的图像保存到文件
    cv2.imwrite('unblur_predictor_out.jpg', out_img)