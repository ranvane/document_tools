import cv2
import numpy as np
import math
# import matplotlib.pyplot as plt


class card_correction:
    def __init__(self, model_path):
        self.model = cv2.dnn.readNet(model_path)
        self.resize_shape = [768, 768]
        self.outlayer_names = self.model.getUnconnectedOutLayersNames()
        self.mean = np.array([0.408, 0.447, 0.470],dtype=np.float32).reshape((1, 1, 3))
        self.std = np.array([0.289, 0.274, 0.278],dtype=np.float32).reshape((1, 1, 3))
        self.K = 10
        self.obj_score = 0.5
        self.out_height = self.resize_shape[0] // 4
        self.out_width = self.resize_shape[1] // 4
    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))
    def ResizePad(self, img, target_size):
        h, w = img.shape[:2]
        m = max(h, w)
        ratio = target_size / m
        new_w, new_h = int(ratio * w), int(ratio * h)
        img = cv2.resize(img, (new_w, new_h), cv2.INTER_LINEAR)
        top = (target_size - new_h) // 2
        bottom = (target_size - new_h) - top
        left = (target_size - new_w) // 2
        right = (target_size - new_w) - left
        img1 = cv2.copyMakeBorder(
            img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(0, 0, 0)
        )
        return img1, new_w, new_h, left, top
    def infer(self, srcimg):
        # 复制输入图像，避免修改原始图像
        self.image = srcimg.copy()
        # 获取输入图像的原始高度和宽度
        ori_h, ori_w = srcimg.shape[:-1]
        # 计算图像的中心点坐标，存储在实例属性 self.c 中
        self.c = np.array([ori_w / 2., ori_h / 2.], dtype=np.float32)
        # 计算图像的最大边长，存储在实例属性 self.s 中
        self.s = max(ori_h, ori_w) * 1.0
        # 调用 preprocess 方法对输入图像进行预处理，得到处理后的图像数据 blob 以及其他相关信息
        blob, new_w, new_h, left, top = self.preprocess(srcimg, self.resize_shape)
        # 将预处理后的图像数据 blob 设置为神经网络模型的输入
        self.model.setInput(blob)
        # 执行前向传播，通过神经网络模型得到预测输出
        pre_out = self.model.forward(self.outlayer_names)
        
        # 调用 postprocess 方法对模型的原始输出进行后处理，得到最终的结果
        out = self.postprocess(pre_out)
        # # 遍历处理后的图像列表，将颜色空间从 BGR 转换为 RGB
        # for i in range(len(out['OUTPUT_IMGS'])):
        #     out['OUTPUT_IMGS'][i] = cv2.cvtColor(out['OUTPUT_IMGS'][i], cv2.COLOR_BGR2RGB)
        # 返回最终处理后的结果
        return out

    def preprocess(self, img, resize_shape):
        im, new_w, new_h, left, top = self.ResizePad(img, resize_shape[0])
        im = (im.astype(np.float32) / 255.0 - self.mean) / self.std
        im = np.expand_dims(im.transpose((2, 0, 1)), axis=0)
        return im.astype(np.float32), new_w, new_h, left, top

    def distance(self, x1, y1, x2, y2):
        return math.sqrt(pow(x1 - x2, 2) + pow(y1 - y2, 2))
    def crop_image(self, img, position):
        x0, y0 = position[0][0], position[0][1]
        x1, y1 = position[1][0], position[1][1]
        x2, y2 = position[2][0], position[2][1]
        x3, y3 = position[3][0], position[3][1]

        img_width = self.distance((x0 + x3) / 2, (y0 + y3) / 2, (x1 + x2) / 2,
                                  (y1 + y2) / 2)
        img_height = self.distance((x0 + x1) / 2, (y0 + y1) / 2, (x2 + x3) / 2,
                                   (y2 + y3) / 2)

        corners_trans = np.zeros((4, 2), np.float32)
        corners_trans[0] = [0, 0]
        corners_trans[1] = [img_width, 0]
        corners_trans[2] = [img_width, img_height]
        corners_trans[3] = [0, img_height]

        transform = cv2.getPerspectiveTransform(position, corners_trans)
        dst = cv2.warpPerspective(img, transform,
                                  (int(img_width), int(img_height)))
        return dst
    def bbox_decode(self,heat, wh, reg=None, K=100):
        batch, cat, height, width = heat.shape

        heat, keep = self._nms(heat)

        scores, inds, clses, ys, xs = self._topk(heat, K=K)
        if reg is not None:
            reg = self._tranpose_and_gather_feat(reg, inds)
            reg = reg.reshape((batch, K, 2))
            xs = xs.reshape((batch, K, 1)) + reg[:, :, 0:1]
            ys = ys.reshape((batch, K, 1)) + reg[:, :, 1:2]
        else:
            xs = xs.reshape((batch, K, 1)) + 0.5
            ys = ys.reshape((batch, K, 1)) + 0.5
        wh = self._tranpose_and_gather_feat(wh, inds)
        wh = wh.reshape((batch, K, 8))
        clses = clses.reshape((batch, K, 1)).astype(np.float32)
        scores = scores.reshape((batch, K, 1))
        bboxes = np.concatenate(
            [
                xs - wh[..., 0:1],
                ys - wh[..., 1:2],
                xs - wh[..., 2:3],
                ys - wh[..., 3:4],
                xs - wh[..., 4:5],
                ys - wh[..., 5:6],
                xs - wh[..., 6:7],
                ys - wh[..., 7:8],
            ],
            axis=2,
        )
        detections = np.concatenate([bboxes, scores, clses, xs, ys], axis=2)

        return detections, inds
    
    
    def _nms(self,heat, kernel=3):
        pad = (kernel - 1) // 2
        hmax = self.max_pool2d(heat, (kernel, kernel), stride=1, padding=pad)
        keep = (hmax == heat).astype(np.float32)
        return heat * keep, keep
    def numpy_topk(self,scores, K, axis=-1):
        indices = np.argsort(-scores, axis=axis).take(np.arange(K), axis=axis)  ### 从大到小排序，取出前K个
        sort_scores = np.take(scores, indices)
        return sort_scores, indices
    def _gather_feat(self,feat, ind, mask=None):
        # print("_gather_feat input shape:", feat.shape, ind.shape)
        dim = feat.shape[2]
        ind = np.tile(np.expand_dims(ind, axis=2), (1, 1, dim))
        feat = np.take_along_axis(feat, ind, axis=1)
        # print("_gather_feat output shape:", feat.shape, ind.shape)
        if mask is not None:
            mask = np.tile(np.expand_dims(mask, axis=2), (1, 1, feat.shape[-1]))
            feat = feat[mask]
            feat = feat.reshape((-1, dim))
        return feat
    def _tranpose_and_gather_feat(self,feat, ind):
        feat = np.transpose(feat, (0, 2, 3, 1))
        feat = feat.reshape((feat.shape[0], -1, feat.shape[3]))
        feat = self._gather_feat(feat, ind)
        return feat
    def _topk(self,scores, K=40):
        batch, cat, height, width = scores.shape

        topk_scores, topk_inds = self.numpy_topk(scores.reshape((batch, cat, -1)), K)

        topk_inds = topk_inds % (height * width)
        topk_ys = (topk_inds / width).astype(np.float32)
        topk_xs = (topk_inds % width).astype(np.float32)

        topk_score, topk_ind = self.numpy_topk(topk_scores.reshape((batch, -1)), K)
        topk_clses = (topk_ind / K).astype(np.int32)
        topk_inds = self._gather_feat(topk_inds.reshape((batch, -1, 1)),topk_ind).reshape((batch, K))
        topk_ys = self._gather_feat(topk_ys.reshape((batch, -1, 1)), topk_ind).reshape((batch, K))
        topk_xs = self._gather_feat(topk_xs.reshape((batch, -1, 1)), topk_ind).reshape((batch, K))

        return topk_score, topk_inds, topk_clses, topk_ys, topk_xs
    def decode_by_ind(self,heat, inds, K=100):
        batch, cat, height, width = heat.shape
        score = self._tranpose_and_gather_feat(heat, inds)
        score = score.reshape((batch, K, cat))
        Type = np.max(score, axis=2)
        return Type
    def get_dir(self,src_point, rot_rad):
        sn, cs = np.sin(rot_rad), np.cos(rot_rad)

        src_result = [0, 0]
        src_result[0] = src_point[0] * cs - src_point[1] * sn
        src_result[1] = src_point[0] * sn + src_point[1] * cs

        return src_result
    def get_3rd_point(self,a, b):
        direct = a - b
        return b + np.array([-direct[1], direct[0]], dtype=np.float32)
    def get_affine_transform(self,center,
                         scale,
                         rot,
                         output_size,
                         shift=np.array([0, 0], dtype=np.float32),
                         inv=0):
        if not isinstance(scale, np.ndarray) and not isinstance(scale, list):
            scale = np.array([scale, scale], dtype=np.float32)

        scale_tmp = scale
        src_w = scale_tmp[0]
        dst_w = output_size[0]
        dst_h = output_size[1]

        rot_rad = np.pi * rot / 180
        src_dir = self.get_dir([0, src_w * -0.5], rot_rad)
        dst_dir = np.array([0, dst_w * -0.5], np.float32)

        src = np.zeros((3, 2), dtype=np.float32)
        dst = np.zeros((3, 2), dtype=np.float32)
        src[0, :] = center + scale_tmp * shift
        src[1, :] = center + src_dir + scale_tmp * shift
        dst[0, :] = [dst_w * 0.5, dst_h * 0.5]
        dst[1, :] = np.array([dst_w * 0.5, dst_h * 0.5], np.float32) + dst_dir

        src[2:, :] = self.get_3rd_point(src[0, :], src[1, :])
        dst[2:, :] = self.get_3rd_point(dst[0, :], dst[1, :])

        if inv:
            trans = cv2.getAffineTransform(np.float32(dst), np.float32(src))
        else:
            trans = cv2.getAffineTransform(np.float32(src), np.float32(dst))

        return trans
    def affine_transform(self,pt, t):
        new_pt = np.array([pt[0], pt[1], 1.0], dtype=np.float32).T
        new_pt = np.dot(t, new_pt)
        return new_pt[:2]
    def transform_preds(self,coords, center, scale, output_size, rot=0):
        target_coords = np.zeros(coords.shape)
        trans = self.get_affine_transform(center, scale, rot, output_size, inv=1)
        for p in range(coords.shape[0]):
            target_coords[p, 0:2] = self.affine_transform(coords[p, 0:2], trans)
        return target_coords
    def bbox_post_process(self,bbox, c, s, h, w):
        for i in range(bbox.shape[0]):
            bbox[i, :, 0:2] = self.transform_preds(bbox[i, :, 0:2], c[i], s[i], (w, h))
            bbox[i, :, 2:4] = self.transform_preds(bbox[i, :, 2:4], c[i], s[i], (w, h))
            bbox[i, :, 4:6] = self.transform_preds(bbox[i, :, 4:6], c[i], s[i], (w, h))
            bbox[i, :, 6:8] = self.transform_preds(bbox[i, :, 6:8], c[i], s[i], (w, h))
            bbox[i, :, 10:12] = self.transform_preds(bbox[i, :, 10:12], c[i], s[i], (w, h))
        return bbox
    
    def nms(self,dets, thresh):
        '''
        len(dets)是batchsize,在推理时batchsize通常等于1, 那就意味着这个函数执行到开头的if就返回了
        即使在推理时输入多张图片, batchsize大于1,也不应该做nms的呀.因为计算多个目标的重叠关系只是在一张图片内做的,多张图片之间计算目标框的
        重叠关系,这个是什么意思呢?
        '''

        if len(dets) < 2:
            return dets
        index_keep = []
        keep = []
        for i in range(len(dets)):
            box = dets[i]
            if box[8] < thresh:
                break
            max_score_index = -1
            ctx = (dets[i][0] + dets[i][2] + dets[i][4] + dets[i][6]) / 4
            cty = (dets[i][1] + dets[i][3] + dets[i][5] + dets[i][7]) / 4
            for j in range(len(dets)):
                if i == j or dets[j][8] < thresh:
                    break
                x1, y1 = dets[j][0], dets[j][1]
                x2, y2 = dets[j][2], dets[j][3]
                x3, y3 = dets[j][4], dets[j][5]
                x4, y4 = dets[j][6], dets[j][7]
                a = (x2 - x1) * (cty - y1) - (y2 - y1) * (ctx - x1)
                b = (x3 - x2) * (cty - y2) - (y3 - y2) * (ctx - x2)
                c = (x4 - x3) * (cty - y3) - (y4 - y3) * (ctx - x3)
                d = (x1 - x4) * (cty - y4) - (y1 - y4) * (ctx - x4)
                if (a > 0 and b > 0 and c > 0 and d > 0) or (a < 0 and b < 0
                                                            and c < 0 and d < 0):
                    if dets[i][8] > dets[j][8] and max_score_index < 0:
                        max_score_index = i
                    elif dets[i][8] < dets[j][8]:
                        max_score_index = -2
                        break
            if max_score_index > -1:
                index_keep.append(max_score_index)
            elif max_score_index == -1:
                index_keep.append(i)
        for i in range(0, len(index_keep)):
            keep.append(dets[index_keep[i]])
        return np.array(keep)
    def draw_show_img(self,img, result, savepath):
        polys = result['POLYGONS']
        centers = result['CENTER']
        angle_cls = result['LABELS']
        bbox = result['BBOX']
        color = (0,0,255)
        for idx, poly in enumerate(polys):
            poly = poly.reshape(4, 2).astype(np.int32)
            ori_center = ((bbox[idx][0]+bbox[idx][2])//2,(bbox[idx][1]+bbox[idx][3])//2)
            img = cv2.drawContours(img,[poly],-1,color,2)
            img = cv2.circle(img,tuple(centers[idx].astype(np.int64).tolist()),5,color,thickness=2)
            img = cv2.circle(img,ori_center,5,color,thickness=2)
            img = cv2.putText(img,str(angle_cls[idx]),ori_center,cv2.FONT_HERSHEY_SIMPLEX,2,color,2)
        cv2.imwrite(savepath,img)
    def max_pool2d(self,input, kernel_size, stride=1, padding=0, return_indices=False):
        batch_size, channels, in_height, in_width = input.shape
        k_height, k_width = kernel_size
        
        out_height = int((in_height + 2 * padding - k_height) / stride) + 1
        out_width = int((in_width + 2 * padding - k_width) / stride) + 1
        out = np.zeros((batch_size, channels, out_height, out_width), dtype=np.float32)
        index = np.zeros((batch_size, channels, out_height, out_width), dtype=np.int64)
        if padding > 0:
            input_ = np.zeros((batch_size, channels, in_height + 2 * padding, in_width + 2 * padding), dtype=np.float32)
            input_[:, :, padding:padding + in_height, padding:padding + in_width] = input
            input = input_

        for b in range(batch_size):
            for c in range(channels):
                for i in range(out_height):
                    for j in range(out_width):
                        start_i = i * stride
                        start_j = j * stride
                        end_i = start_i + k_height
                        end_j = start_j + k_width
                        Xi = input[b, c, start_i: end_i, start_j: end_j]
    
                        max_value = np.max(Xi)
                        k = np.argmax(Xi)
                        Ia = k // k_height + start_i - padding
                        Ib = k % k_width + start_j - padding
                        Ia = Ia if Ia > 0 else 0
                        Ib = Ib if Ib > 0 else 0
                        max_index = Ia * in_width + Ib
                        out[b, c, i, j] = max_value
                        index[b, c, i, j] = max_index

        if return_indices:
            return out, index
        else:
            return out
    def postprocess(self, output):
        reg = output[3]
        wh = output[2]
        hm = output[4]
        angle_cls = output[0]
        ftype_cls = output[1]
        
        hm = self.sigmoid(hm)
        angle_cls = self.sigmoid(angle_cls)
        ftype_cls = self.sigmoid(ftype_cls)

        bbox, inds = self.bbox_decode(hm, wh, reg=reg, K=self.K)
        angle_cls = self.decode_by_ind(angle_cls, inds, K=self.K)
        ftype_cls = self.decode_by_ind(ftype_cls, inds,K=self.K).astype(np.float32)

        for i in range(bbox.shape[1]):
            bbox[0][i][9] = angle_cls[0][i]
        bbox = np.concatenate((bbox, np.expand_dims(ftype_cls, axis=-1)),axis=-1)
        # bbox = nms(bbox, 0.3)
        bbox = self.bbox_post_process(bbox.copy(), [self.c], [self.s], self.out_height, self.out_width)
        res = []
        angle = []
        sub_imgs = []
        ftype = []
        score = []
        center = []
        corner_left_right = []
        for idx, box in enumerate(bbox[0]):
            if box[8] > self.obj_score:
                angle.append(int(box[9]))
                res.append(box[0:8])
                box8point = np.array(box[0:8]).reshape(4,2).astype(np.int32)
                corner_left_right.append([box8point[:,0].min(),box8point[:,1].min(),box8point[:,0].max(),box8point[:,1].max()])
                sub_img = self.crop_image(self.image,res[-1].copy().reshape(4, 2))
                if angle[-1] == 1:
                    sub_img = cv2.rotate(sub_img, 2)
                if angle[-1] == 2:
                    sub_img = cv2.rotate(sub_img, 1)
                if angle[-1] == 3:
                    sub_img = cv2.rotate(sub_img, 0)
                sub_imgs.append(sub_img)
                ftype.append(int(box[12]))
                score.append(box[8])
                center.append([box[10],box[11]])

        result = {
            "POLYGONS": np.array(res),
            "BBOX": np.array(corner_left_right),
            "SCORES": np.array(score),
            "OUTPUT_IMGS": sub_imgs,
            "LABELS": np.array(angle),
            "LAYOUT": np.array(ftype),
            "CENTER": np.array(center)
        }
        return result
    
if __name__ == "__main__":
    imgpath = 'testimgs/7.jpg'
    model_path = 'cv_resnet18_card_correction.onnx'
    mynet = card_correction(model_path)
    
    with open(imgpath, 'rb') as f:
        img_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
    srcimg = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    
    out = mynet.infer(srcimg)
    # # 假设只显示处理后的第一张图像
    if out['OUTPUT_IMGS']:
        processed_img = out['OUTPUT_IMGS'][0]
        processed_img_rgb = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)


    # 将 BGR 格式转换为 RGB 格式
    # srcimg_rgb = cv2.cvtColor(srcimg, cv2.COLOR_BGR2RGB)

    # # 假设只显示处理后的第一张图像
    # if out['OUTPUT_IMGS']:
    #     processed_img = out['OUTPUT_IMGS'][0]
    #     processed_img_rgb = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

    #     # 创建一个包含两个子图的画布
    #     fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    #     # 显示原图
    #     axes[0].imshow(srcimg_rgb)
    #     axes[0].set_title('Original Image')
    #     axes[0].axis('off')

    #     # 显示处理后的图像
    #     axes[1].imshow(processed_img_rgb)
    #     axes[1].set_title('Processed Image')
    #     axes[1].axis('off')

    #     # 显示图像
    #     plt.show()