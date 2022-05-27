#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Copyright (c) Megvii, Inc. and its affiliates.

import os

from yolox.exp import Exp as MyExp
from yolox.models import YOLOX, YOLOPAFPN, YOLOXHead

class Exp(MyExp):
    def __init__(self):
        super(Exp, self).__init__()

        self.depth = 0.33
        self.width = 0.50

        self.max_epoch = 1000
        self.num_classes = 4
        self.input_size = (320, 320)
        self.test_size = (320, 320)

        self.data_dir_train = None
        self.data_dir_test = None
        self.train_ann = None
        self.test_ann = None

        self.exp_name = os.path.split(os.path.realpath(__file__))[1].split(".")[0]

        # 此处增加新增的模型
        if getattr(self, "model", None) is None:
            pass
            # example = torch.rand(size=(1,3,*self.test_size), dtype=torch.float32)
            # in_channels = [256, 512, 1024]
            # backbone = YOLOPAFPN(self.depth, self.width, in_channels=in_channels, act=self.act)
            # head = YOLOXHead(self.num_classes, self.width, in_channels=in_channels, act=self.act)
            # self.model = YOLOX(backbone, head)
