# 基于yolox的旋转目标检测
    把角度量化到0-179度之间，把角度看作一个分类问题，对目标角度进行预测，角度损失函数使用二值交叉熵损失。

## 1. 数据准备及参数设置
    支持coco格式数据和DOTA格式数据，修改exps/default/xxxx.py

## 2. 网络训练
    python train.py 

## 3. 推理测试
    python demo.py image

## 参考资料
    https://github.com/Megvii-BaseDetection/YOLOX