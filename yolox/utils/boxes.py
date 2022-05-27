#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Copyright (c) Megvii Inc. All rights reserved.

import math
import numpy as np
import cv2

import torch
import torchvision

import pyiou

__all__ = [
    "filter_box",
    "postprocess",
    "bboxes_iou",
    "matrix_iou",
    "adjust_box_anns",
    "xyxy2xywh",
    "xyxy2cxcywh",
    "x1y1x2y2x3y3x4y4_to_cxcywha"
]


def filter_box(output, scale_range):
    """
    output: (N, 5+class) shape
    """
    min_scale, max_scale = scale_range
    w = output[:, 2] - output[:, 0]
    h = output[:, 3] - output[:, 1]
    keep = (w * h > min_scale * min_scale) & (w * h < max_scale * max_scale)
    return output[keep]


def non_max_suppression(detections, nms_thres=0.4, class_agnostic=False):

    # Detections ordered as (cx, cy, w, h, obj_conf, class_conf, class_pred, angle)
    detections = detections.cpu()
    if not class_agnostic:
        # detections = torch.cat((pred[:, :9], class_prob.float().unsqueeze(1), class_pred.float().unsqueeze(1)), 1)
        # Iterate through all predicted classes
        unique_labels = detections[:, 6].cpu().unique()

        outputs = []
        for c in unique_labels:
            detections_class = detections[detections[:, 6] == c]

            all_pts = []
            for d in detections_class:
                x, y, w, h = d[:4].numpy()
                angle = d[-1].item()
                if w < h:
                    h, w = w, h
                    angle += 90
                rotate_box = ((x, y), (h, w), angle)
                # print('rotate_box: ', rotate_box)
                pts = cv2.boxPoints(rotate_box)
                pt4 = [pts[0, 0], pts[0, 1], pts[1, 0], pts[1, 1], pts[2, 0], pts[2, 1], pts[3, 0], pts[3, 1]]
                all_pts.append(pt4)
            all_pts = np.array(all_pts)

            ious = pyiou.get_ious_4pts(all_pts.copy())

            scores = detections_class[:, -4] * detections_class[:, -3]
            # print('scores: ', scores)
            keep = pyiou.fast_ious_process_4pts(ious, scores, nms_thres)
            detections_class = detections_class[keep]
            outputs.append(detections_class)

        outputs = torch.cat(outputs)
        return outputs
    else:
        detections_class = detections

        all_pts = []
        for d in detections_class:
            x, y, w, h = d[:4].numpy()
            angle = d[-1].item()
            if w < h:
                h, w = w, h
                angle += 90
            rotate_box = ((x,y), (h,w), angle)
            #print('rotate_box: ', rotate_box)
            pts = cv2.boxPoints(rotate_box)
            pt4 = [pts[0,0], pts[0,1], pts[1,0], pts[1,1], pts[2,0], pts[2,1], pts[3,0], pts[3,1]]
            all_pts.append(pt4)
        all_pts = np.array(all_pts)

        ious = pyiou.get_ious_4pts(all_pts.copy())
        scores = detections_class[:, -4] * detections_class[:, -3]
        keep = pyiou.fast_ious_process_4pts(ious, scores, nms_thres)
        detections_class = detections_class[keep]

        return detections_class


def postprocess(prediction, num_classes, conf_thre=0.7, nms_thre=0.45, class_agnostic=False):
    # [x y w h obj_conf cls... angle...]
    output = [None for _ in range(len(prediction))]
    for i, image_pred in enumerate(prediction):

        # If none are remaining => process next image
        if not image_pred.size(0):
            continue
        # Get score and class with highest confidence
        class_conf, class_pred = torch.max(image_pred[:, 5: 5 + num_classes], 1, keepdim=True)

        # get angle and angle confidence
        angle_conf, angle_pred = torch.max(image_pred[:, 5 + num_classes:], 1, keepdim=True)

        conf_mask = (image_pred[:, 4] * class_conf.squeeze() >= conf_thre).squeeze()
        # Detections ordered as (cx, cy, w, h, obj_conf, class_conf, class_pred, angle)
        detections = torch.cat((image_pred[:, :5], class_conf, class_pred.float(), angle_pred.float()), 1)
        detections = detections[conf_mask]
        if not detections.size(0):
            continue

        detections = non_max_suppression(detections, nms_thre, class_agnostic)
        if output[i] is None:
            output[i] = detections
        else:
            output[i] = torch.cat((output[i], detections))

        #exit(0)

    return output


def bboxes_iou(bboxes_a, bboxes_b, xyxy=True):
    if bboxes_a.shape[1] != 4 or bboxes_b.shape[1] != 4:
        raise IndexError

    if xyxy:
        tl = torch.max(bboxes_a[:, None, :2], bboxes_b[:, :2])
        br = torch.min(bboxes_a[:, None, 2:], bboxes_b[:, 2:])
        area_a = torch.prod(bboxes_a[:, 2:] - bboxes_a[:, :2], 1)
        area_b = torch.prod(bboxes_b[:, 2:] - bboxes_b[:, :2], 1)
    else:
        tl = torch.max(
            (bboxes_a[:, None, :2] - bboxes_a[:, None, 2:] / 2),
            (bboxes_b[:, :2] - bboxes_b[:, 2:] / 2),
        )
        br = torch.min(
            (bboxes_a[:, None, :2] + bboxes_a[:, None, 2:] / 2),
            (bboxes_b[:, :2] + bboxes_b[:, 2:] / 2),
        )

        area_a = torch.prod(bboxes_a[:, 2:], 1)
        area_b = torch.prod(bboxes_b[:, 2:], 1)
    en = (tl < br).type(tl.type()).prod(dim=2)
    area_i = torch.prod(br - tl, 2) * en  # * ((tl < br).all())
    return area_i / (area_a[:, None] + area_b - area_i)


def matrix_iou(a, b):
    """
    return iou of a and b, numpy version for data augenmentation
    """
    lt = np.maximum(a[:, np.newaxis, :2], b[:, :2])
    rb = np.minimum(a[:, np.newaxis, 2:], b[:, 2:])

    area_i = np.prod(rb - lt, axis=2) * (lt < rb).all(axis=2)
    area_a = np.prod(a[:, 2:] - a[:, :2], axis=1)
    area_b = np.prod(b[:, 2:] - b[:, :2], axis=1)
    return area_i / (area_a[:, np.newaxis] + area_b - area_i + 1e-12)


def adjust_box_anns(bbox, scale_ratio, padw, padh, w_max, h_max):
    bbox[:, 0::2] = np.clip(bbox[:, 0::2] * scale_ratio + padw, 0, w_max)
    bbox[:, 1::2] = np.clip(bbox[:, 1::2] * scale_ratio + padh, 0, h_max)
    return bbox


def xyxy2xywh(bboxes):
    bboxes[:, 2] = bboxes[:, 2] - bboxes[:, 0]
    bboxes[:, 3] = bboxes[:, 3] - bboxes[:, 1]
    return bboxes


def xyxy2cxcywh(bboxes):
    bboxes[:, 2] = bboxes[:, 2] - bboxes[:, 0]
    bboxes[:, 3] = bboxes[:, 3] - bboxes[:, 1]
    bboxes[:, 0] = bboxes[:, 0] + bboxes[:, 2] * 0.5
    bboxes[:, 1] = bboxes[:, 1] + bboxes[:, 3] * 0.5
    return bboxes

def order_points(pts):
    ''' sort rectangle points by clockwise '''
    sort_x = pts[np.argsort(pts[:, 0]), :]

    Left = sort_x[:2, :]
    Right = sort_x[2:, :]
    # Left sort
    Left = Left[np.argsort(Left[:, 1])[::-1], :]
    # Right sort
    Right = Right[np.argsort(Right[:, 1]), :]

    return np.concatenate((Left, Right), axis=0)


def x1y1x2y2x3y3x4y4_to_cxcywha(bboxes):
    bboxes_t = []
    for bbox in bboxes:
        pts = np.reshape(np.float32(bbox), (len(bbox)//2,2))
        rect = cv2.minAreaRect(pts)

        x = rect[0][0]
        y = rect[0][1]
        w = rect[1][1]
        h = rect[1][0]
        angle = math.ceil(rect[2])

        if w < h:
            h, w = w, h
            angle += 90

        angle = min(179, max(0, angle))
        b = [x, y, w, h, angle]
        bboxes_t.append(b)
    return np.array(bboxes_t, dtype=np.float32)


def x1y1x2y2x3y3x4y4_to_cxcywha_bak(bboxes):
    bboxes_t = []
    for bbox in bboxes:
        pts = np.reshape(np.float32(bbox), (len(bbox)//2,2))
        rect = cv2.minAreaRect(pts)
        x = rect[0][0]
        y = rect[0][1]
        w = rect[1][1]
        h = rect[1][0]
        angle = math.ceil(rect[2])
        angle = min(89, max(0, angle))
        b = [x, y, w, h, angle]
        bboxes_t.append(b)
    return np.array(bboxes_t, dtype=np.float32)