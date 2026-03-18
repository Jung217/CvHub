"""
第二遍：為 cvpr/2022 下的 HTML 檔案補齊中文翻譯區塊（zh-text）中缺少的高亮。
此版本處理較長的句子級高亮（thesis、evidence、method、rebuttal），
透過在 en-text 和 zh-text 之間建立段落內的對應關係。

策略：對於每個英文高亮片段，在對應的中文段落中找到翻譯後的等價片段，加上相同的 hl- class。
"""

import re
import os


def extract_hl_spans_with_pos(html_text):
    """擷取所有 hl-* spans，含位置資訊"""
    pattern = r'<span\s+class="(hl-(?:thesis|concept|evidence|rebuttal|method))">(.*?)</span>'
    results = []
    for m in re.finditer(pattern, html_text, re.DOTALL):
        hl_class = m.group(1)
        inner = m.group(2)
        clean = re.sub(r'<[^>]+>', '', inner).strip()
        results.append({
            'class': hl_class,
            'text': clean,
            'inner_html': inner,
            'start': m.start(),
            'end': m.end(),
            'full_match': m.group(0)
        })
    return results


def get_plain_text(html):
    """移除 HTML 標籤取得純文字"""
    return re.sub(r'<[^>]+>', '', html)


def find_sentence_in_zh(en_span_text, en_full_text, zh_html):
    """
    對於一個英文高亮片段，嘗試在中文文字中找到對應的翻譯。

    策略：
    1. 找出英文高亮在英文段落中的位置（比例）
    2. 根據高亮前後的英文文字上下文，在中文中定位
    3. 使用句子邊界作為輔助
    """
    zh_plain = get_plain_text(zh_html)
    en_plain = get_plain_text(en_full_text)

    # 找出高亮文字在英文中的位置
    en_pos = en_plain.find(en_span_text)
    if en_pos == -1:
        return None

    # 計算位置比例
    en_ratio_start = en_pos / max(len(en_plain), 1)
    en_ratio_end = (en_pos + len(en_span_text)) / max(len(en_plain), 1)

    # 找出英文高亮前後的句子邊界
    # 用句號、分號、逗號等切分

    # 計算中文的對應位置（近似）
    zh_approx_start = int(en_ratio_start * len(zh_plain))
    zh_approx_end = int(en_ratio_end * len(zh_plain))

    return zh_approx_start, zh_approx_end


# ===== 每個檔案的具體修補對照表 =====
# 格式：{filename: [(para_index, hl_class, zh_search_text), ...]}
# para_index 從 0 開始

MANUAL_FIXES = {
    "convnext.html": [
        # Para 1 (abstract)
        (0, "hl-rebuttal", "然而，原始 ViT 在應用於物件偵測與語意分割等通用電腦視覺任務時遭遇困難"),
        (0, "hl-thesis", "重新審視設計空間，測試純摺積網路所能達成的極限"),
        (0, "hl-method", "逐步將標準 ResNet「現代化」，使其趨近 Vision Transformer 的設計"),
        (0, "hl-evidence", "在精確度與可擴展性上與 Transformer 相當甚至更優，達到 87.8% 的 ImageNet top-1 精確度，並在 COCO 偵測與 ADE20K 分割上超越 Swin Transformer"),
        # Para 2
        (1, "hl-concept", "「轟轟烈烈的 2020 年代」"),
        (1, "hl-concept", "視覺 Transformer（ViT）"),
        (1, "hl-concept", "摺積神經網路（ConvNet）"),
        (1, "hl-concept", "VGGNet、ResNet、DenseNet 與 EfficientNet"),
        (1, "hl-thesis", "固有優勢：平移等變性"),
        (1, "hl-thesis", "透過滑動視窗共享計算的效率"),
        # Para 3
        (2, "hl-concept", "視覺 Transformer（ViT）"),
        (2, "hl-rebuttal", "原始 ViT 引入的影像特定歸納偏置極少"),
        (2, "hl-evidence", "在影像分類上展現優越的擴展行為"),
        (2, "hl-rebuttal", "全域注意力機制的二次方複雜度"),
        (2, "hl-concept", "階層式 Transformer"),
        (2, "hl-method", "重新引入滑動視窗策略與其他 ConvNet 先驗"),
        (2, "hl-thesis", "此優越性究竟源自 Transformer 的固有優勢，還是僅僅源自重新納入摺積基礎的原則？"),
        # Para 4
        (3, "hl-thesis", "「Transformer 中的設計決策如何影響 ConvNet 的效能？」"),
        (3, "hl-method", "逐步將 ResNet 現代化至 Swin Transformer 的設計"),
        (3, "hl-evidence", "達到 87.8% 的 ImageNet top-1 精確度，在 COCO 偵測與 ADE20K 分割上超越 Swin Transformer"),
        (3, "hl-thesis", "保持標準 ConvNet 的簡潔與高效"),
        (3, "hl-thesis", "許多從 Transformer 借鑑的設計選擇，在過去十年的 ConvNet 文獻中已被個別探索，但從未被集體組裝"),
        # Para 5 (training)
        (4, "hl-thesis", "訓練程序也顯著影響效能"),
        (4, "hl-method", "訓練週期從 ResNet 原本的 90 個 epoch 延長至 300 個 epoch"),
        (4, "hl-method", "AdamW 最佳化器"),
        (4, "hl-method", "Mixup、Cutmix、RandAugment、Random Erasing"),
        (4, "hl-method", "Stochastic Depth 與 Label Smoothing"),
        # Para 6
        (5, "hl-evidence", "將 ResNet-50 的效能從 76.1% 提升至 78.8%（提升 2.7%）"),
        (5, "hl-thesis", "傳統 ConvNet 與 Vision Transformer 之間的效能差距，有很大一部分可能歸因於訓練技術"),
        (5, "hl-method", "ImageNet-1K 精確度均為三次隨機種子的平均值"),
        # Para 7 (macro)
        (6, "hl-concept", "res4 階段"),
        (6, "hl-evidence", "14x14 特徵平面"),
        (6, "hl-method", "階段計算比例 1:1:3:1"),
        (6, "hl-method", "從 (3, 4, 6, 3) 調整為 (3, 3, 9, 3)"),
        (6, "hl-evidence", "精確度從 78.8% 提升至 79.4%"),
        # Para 8 (patchify)
        (7, "hl-concept", "ResNet 的 stem"),
        (7, "hl-method", "步幅為 2 的 7x7 摺積加上最大池化"),
        (7, "hl-concept", "「patchify」策略"),
        (7, "hl-method", "大核心（14 或 16）與非重疊摺積"),
        (7, "hl-method", "較小的 patch 大小 4"),
        (7, "hl-method", "4x4 步幅為 4 的摺積層"),
        (7, "hl-evidence", "從 79.4% 變為 79.5%"),
        # Para 9 (ResNeXt) - 已大部分處理，補上剩餘
        (8, "hl-method", "分組數等於通道數"),
        (8, "hl-thesis", "「深度可分離摺積類似於自注意力中的加權求和運算，以逐通道方式運作，即僅在空間維度上混合資訊。」"),
        (8, "hl-method", "將網路寬度從 64 擴展至 96 個通道"),
        (8, "hl-evidence", "效能提升至 80.5%，FLOPs 為 5.3G"),
        # Para 10 (inverted bottleneck)
        (9, "hl-concept", "反轉瓶頸"),
        (9, "hl-method", "MLP 的隱藏維度是輸入維度的四倍"),
        (9, "hl-evidence", "整體網路 FLOPs 反而降至 4.6G"),
        (9, "hl-evidence", "效能從 80.5% 微幅提升至 80.6%"),
        (9, "hl-evidence", "從 81.9% 提升至 82.6%，且 FLOPs 減少"),
        # Para 11 (large kernel)
        (10, "hl-rebuttal", "3x3 堆疊作為黃金標準"),
        (10, "hl-concept", "Swin Transformer"),
        (10, "hl-method", "至少 7x7 的視窗大小"),
        (10, "hl-method", "深度可分離摺積層重新定位到稠密 1x1 層之前"),
        (10, "hl-method", "MSA 區塊置於 MLP 層之前"),
        (10, "hl-evidence", "FLOPs 降至 4.1G，但效能暫時下降至 79.9%"),
        # Para 12 (kernel sizes)
        (11, "hl-method", "大核心的採用"),
        (11, "hl-method", "核心大小 3、5、7、9 與 11"),
        (11, "hl-evidence", "效能從 79.9%（3x3）提升至 80.6%（7x7）"),
        (11, "hl-thesis", "「較大核心的收益在 7x7 時達到飽和點。」"),
        (11, "hl-evidence", "「ResNet-200 規模的模型在核心大小超過 7x7 時不再展現進一步增益。」"),
        (11, "hl-thesis", "ConvNet 與 Transformer 之間最佳感受野大小的趨同"),
        # Para 13 (GELU)
        (12, "hl-concept", "修正線性單元（ReLU）"),
        (12, "hl-concept", "高斯誤差線性單元（GELU）"),
        (12, "hl-concept", "BERT、GPT-2 與 ViT"),
        (12, "hl-evidence", "「精確度保持不變（80.6%）」"),
        # Para 14 (fewer activations)
        (13, "hl-thesis", "更少的啟動函數"),
        (13, "hl-method", "在 MLP 區塊中僅包含一個啟動函數"),
        (13, "hl-evidence", "效能提升 0.7% 至 81.3%"),
        (13, "hl-evidence", "「實質上已追平 Swin-T 的效能」"),
        # Para 15 (fewer norm)
        (14, "hl-evidence", "效能提升至 81.4%"),
        (14, "hl-evidence", "「已超越 Swin-T 的成績」"),
        # Para 16 (BN to LN)
        (15, "hl-concept", "批次正規化（BN）"),
        (15, "hl-concept", "層正規化（LN）"),
        (15, "hl-rebuttal", "先前在原始 ResNet 中直接替換 BN 時效果不佳"),
        (15, "hl-evidence", "「我們的 ConvNet 模型使用 LN 訓練毫無困難；事實上效能略為提升，達到 81.5% 的精確度。」"),
        # Para 17 (separate downsample)
        (16, "hl-method", "透過殘差區塊使用步幅為 2 的 3x3 摺積進行空間下取樣"),
        (16, "hl-method", "階段之間使用獨立的下取樣層"),
        (16, "hl-method", "2x2 步幅為 2 的摺積進行下取樣"),
        (16, "hl-rebuttal", "訓練發散"),
        (16, "hl-method", "在空間解析度變化處加入正規化"),
        (16, "hl-evidence", "精確度提升至 82.0%"),
        (16, "hl-evidence", "「顯著超越 Swin-T 的 81.3%。」"),
        (16, "hl-thesis", "「這些設計在 ConvNet 文獻中並非新穎——它們在過去十年中已被個別研究，但從未被集體組裝。」"),
        # Para 18 (results)
        (17, "hl-evidence", "ConvNeXt-T 達到 82.1% 精確度，對比 Swin-T 的 81.3%"),
        (17, "hl-evidence", "ConvNeXt-B 達到 85.1%，對比 Swin-B 的 84.5%"),
        (17, "hl-evidence", "95.7 對比 85.1 image/s"),
        (17, "hl-evidence", "29M 參數、4.5G FLOPs"),
        (17, "hl-evidence", "50M 參數、8.7G FLOPs"),
        (17, "hl-evidence", "89M 參數、15.4G FLOPs"),
        (17, "hl-evidence", "198M 參數、34.4G FLOPs"),
        (17, "hl-evidence", "350M 參數、60.9G FLOPs"),
        # Para 19 (22K pretrain)
        (18, "hl-method", "ImageNet-22K 預訓練與微調"),
        (18, "hl-evidence", "ConvNeXt-XL 達到 87.8% 精確度"),
        (18, "hl-evidence", "EfficientNetV2-XL（87.3%）"),
        (18, "hl-evidence", "ConvNeXt-B 達到 86.8%，對比 Swin-B 的 86.4%"),
        (18, "hl-thesis", "ConvNet 能有效地隨更大的資料集擴展，挑戰了關於 Transformer 在大資料量環境中具有優越性的普遍看法"),
        # Para 20 (isotropic)
        (19, "hl-concept", "非階層式（等向）架構"),
        (19, "hl-evidence", "等向 ConvNeXt-B 達到 82.0% 精確度，匹配 ViT-B 的效能"),
        (19, "hl-thesis", "ConvNeXt 區塊設計即使在缺乏從 ConvNet 傳統借鑑的階層式多階段結構時也同樣有效"),
        # Para 21 (COCO)
        (20, "hl-evidence", "ConvNeXt-T 達到 46.2 APbox 與 41.7 APmask"),
        (20, "hl-evidence", "Swin-T 的 46.0 APbox 與 41.6 APmask"),
        (20, "hl-evidence", "ConvNeXt-B 達到 54.0 APbox 與 46.9 APmask"),
        (20, "hl-evidence", "Swin-B 的 53.0 APbox 與 45.8 APmask"),
        # Para 22 (ADE20K)
        (21, "hl-evidence", "ConvNeXt-T 達到 46.7 mIoU"),
        (21, "hl-evidence", "Swin-T 的 45.8 mIoU"),
        (21, "hl-evidence", "ConvNeXt-L 達到 54.0 mIoU"),
        (21, "hl-evidence", "Swin-L 的 53.5 mIoU"),
        (21, "hl-thesis", "ConvNeXt 架構在分類之外的下游視覺任務中也同樣有效"),
        # Para 23 (efficiency)
        (22, "hl-rebuttal", "深度可分離摺積的效率疑慮"),
        (22, "hl-evidence", "「ConvNeXt 的推論吞吐量與 Swin Transformer 相當甚至更高」"),
        (22, "hl-evidence", "ConvNeXt-B 的訓練記憶體消耗為 17.4GB，對比 Swin-B 的 18.5GB"),
        (22, "hl-evidence", "「最高 49% 的吞吐量提升」"),
        (22, "hl-thesis", "純摺積網路可以同時比階層式 Transformer 更快且更精確"),
        # Para 24 (robustness)
        (23, "hl-evidence", "ConvNeXt 在 ImageNet-A 上超越 Swin-T（39.5% 對 21.7%）"),
        (23, "hl-evidence", "在 ImageNet-C 上表現更佳（39.2 對 41.5 mCE，越低越好）"),
        (23, "hl-evidence", "在 ImageNet-R 與 ImageNet-Sketch 上也維持優勢"),
        (23, "hl-thesis", "現代化 ConvNet 在穩健性方面並不遜於 Transformer"),
        # Para 25 (conclusion)
        (24, "hl-thesis", "純摺積模型在多種視覺基準上能與最先進的階層式 Vision Transformer 競爭甚至超越"),
        (24, "hl-thesis", "許多從 Transformer 借鑑的設計選擇可以被原生摺積實作有效複製"),
        (24, "hl-method", "系統性的現代化方法論"),
    ],

    "dndetr.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "DETR"),
        (0, "hl-thesis", "緩慢的訓練收斂問題"),
        (0, "hl-method", "去噪訓練"),
        (0, "hl-evidence", "在 12 個訓練週期下提升了 1.9 AP"),
        (0, "hl-evidence", "相較於 DAB-DETR 基線提升了 1.9 AP"),
        # Para 2
        (1, "hl-concept", "DETR"),
        (1, "hl-method", "集合預測"),
        (1, "hl-method", "二分圖匹配"),
        (1, "hl-concept", "匈牙利演算法"),
        (1, "hl-thesis", "DETR 面臨顯著的緩慢訓練收斂問題"),
        (1, "hl-evidence", "需要 500 個訓練週期才能達到收斂"),
        # Para 3
        (2, "hl-concept", "Deformable DETR"),
        (2, "hl-method", "多尺度可變形注意力"),
        (2, "hl-concept", "Conditional DETR"),
        (2, "hl-method", "條件交叉注意力"),
        (2, "hl-concept", "DAB-DETR"),
        (2, "hl-method", "動態錨框"),
        (2, "hl-thesis", "匈牙利匹配的不穩定性是收斂緩慢的核心原因"),
        # Para 4
        (3, "hl-method", "去噪訓練"),
        (3, "hl-thesis", "將去噪作為加速收斂的輔助任務"),
        (3, "hl-method", "對真實邊界框和類別標籤添加噪聲"),
        (3, "hl-method", "注意力遮罩防止資訊洩漏"),
        (3, "hl-thesis", "為 Transformer 解碼器提供穩定的初始錨點"),
        # Para 5
        (4, "hl-evidence", "在 DAB-DETR 上提升了 1.9 AP"),
        (4, "hl-evidence", "在 Deformable DETR 上提升了 1.5 AP"),
        (4, "hl-thesis", "DN 方法可作為通用的即插即用元件"),
        # Para 6 (related - deformable)
        (5, "hl-concept", "DETR"),
        (5, "hl-method", "Transformer 編碼器-解碼器"),
        (5, "hl-method", "可學習的物件查詢"),
        (5, "hl-concept", "Deformable DETR"),
        (5, "hl-method", "多尺度可變形注意力"),
        (5, "hl-concept", "Conditional DETR"),
        (5, "hl-concept", "Anchor DETR"),
        (5, "hl-concept", "DAB-DETR"),
        # Para 7 (denoising related) - 已處理大部分
        (6, "hl-method", "表示學習與生成式建模"),
        (6, "hl-method", "輔助訓練任務"),
        # Para 8 (architecture)
        (7, "hl-method", "四維錨框 (x, y, w, h)"),
        (7, "hl-method", "匹配查詢"),
        (7, "hl-method", "注意力遮罩"),
        (7, "hl-thesis", "DN-DETR 在測試時不引入任何額外計算量"),
        # Para 9 (noise)
        (8, "hl-method", "中心偏移噪聲"),
        (8, "hl-method", "尺度縮放噪聲"),
        (8, "hl-method", "類別標籤翻轉噪聲"),
        (8, "hl-method", "多個去噪群組"),
        # Para 10 (attention mask)
        (9, "hl-method", "注意力遮罩"),
        (9, "hl-thesis", "防止去噪查詢與匹配查詢之間的資訊洩漏"),
        (9, "hl-method", "對角線區塊結構"),
        # Para 11 (loss)
        (10, "hl-method", "重建損失"),
        (10, "hl-method", "去噪損失由分類損失與框迴歸損失組成"),
        (10, "hl-method", "L1 損失與 GIoU 損失"),
        # Para 12 (ablation)
        (11, "hl-evidence", "去噪訓練帶來 1.9 AP 的提升"),
        (11, "hl-evidence", "噪聲規模 = 0.4 為最佳"),
        (11, "hl-evidence", "5 個去噪群組取得最佳的精確度-效率平衡"),
        # Para 13 (convergence)
        (12, "hl-evidence", "DN-DETR 僅需 12 個訓練週期即能匹配 DAB-DETR 50 個週期的效能"),
        (12, "hl-thesis", "去噪提供的穩定梯度在訓練初期尤其關鍵"),
        # Para 14 (AP results)
        (13, "hl-evidence", "DN-DETR + ResNet-50 在 12 個週期達到 44.4 AP"),
        (13, "hl-evidence", "50 個週期時進一步提升至 46.5 AP"),
        (13, "hl-evidence", "搭配 Swin-L 骨幹時更達到 58.0 AP"),
        # Para 15 (generalizability)
        (14, "hl-evidence", "DAB-DETR 上提升 +1.9 AP"),
        (14, "hl-evidence", "Deformable DETR 上提升 +1.5 AP"),
        (14, "hl-evidence", "DN-Deformable-DETR 在 12 個週期即達到 48.6 AP"),
        # Para 16-21 depend on content...
    ],

    "dualshutter.html": [
        # 此檔已全部處理，不需額外修補
    ],

    "epropnp.html": [
        # 此檔已全部處理
    ],

    "ldm.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "潛在擴散模型"),
        (0, "hl-method", "感知壓縮階段"),
        (0, "hl-method", "在潛在空間中訓練擴散模型"),
        (0, "hl-thesis", "在影像生成品質與計算效率之間達成接近最佳的平衡"),
        (0, "hl-evidence", "在多項基準上達到最先進或具競爭力的表現"),
        # Para 2
        (1, "hl-concept", "擴散模型"),
        (1, "hl-thesis", "在影像合成方面取得了最先進的結果"),
        (1, "hl-rebuttal", "直接在高維像素空間中運作，導致推論成本極高且訓練費用昂貴"),
        (1, "hl-method", "將訓練分為感知壓縮階段與語意生成階段"),
        # Para 3 (perceptual compression)
        (2, "hl-method", "感知壓縮"),
        (2, "hl-concept", "自編碼器"),
        (2, "hl-method", "將影像編碼至低維潛在空間"),
        (2, "hl-thesis", "去除高頻、無法感知的細節"),
        # Para 4 (diffusion in latent)
        (3, "hl-method", "去噪擴散機率模型"),
        (3, "hl-method", "在潛在空間中訓練"),
        (3, "hl-thesis", "大幅降低計算需求"),
        # Para 5 (conditioning)
        (4, "hl-method", "交叉注意力機制"),
        (4, "hl-method", "領域專用編碼器"),
        (4, "hl-thesis", "統一且靈活的條件生成框架"),
        # Para 6 (related - DMs)
        (5, "hl-concept", "去噪擴散機率模型"),
        (5, "hl-method", "前向擴散過程與學習的逆向去噪過程"),
        (5, "hl-concept", "分數匹配"),
        (5, "hl-evidence", "在影像合成方面超越 GAN"),
        # Para 7 (related - 2stage)
        (6, "hl-concept", "VQ-VAE"),
        (6, "hl-concept", "VQGAN"),
        (6, "hl-method", "先將影像壓縮為離散潛在碼，再訓練自迴歸模型"),
        (6, "hl-thesis", "LDM 在連續潛在空間中操作擴散模型，無需向量量化"),
        # Para 8 (autoencoder)
        (7, "hl-method", "感知損失與對抗損失"),
        (7, "hl-method", "KL 正則化與 VQ 正則化"),
        (7, "hl-thesis", "確保潛在空間的變異數有界"),
        # Para 9 (LDM loss)
        # 已大部分處理
        # Para 10 (conditioning mechanism)
        (9, "hl-method", "交叉注意力"),
        (9, "hl-method", "領域專用編碼器"),
        (9, "hl-thesis", "能處理文字、語意佈局、影像等多種模態"),
        # Para 11 (unconditional)
        (10, "hl-evidence", "在 CelebA-HQ 256 上達到 5.11 的 FID"),
        (10, "hl-evidence", "在 LSUN-Bedrooms 256 上達到 2.95 的 FID"),
        # Para 12 (text-to-image)
        (11, "hl-evidence", "在 MS-COCO 上達到 12.63 的 FID"),
        (11, "hl-method", "BERT 文字編碼器"),
        # Para 13 (layout)
        (12, "hl-evidence", "在 COCO 上達到 40.91 的 FID"),
        # Para 14-17 more results...
        (17, "hl-evidence", "在影像修補方面，在 Places 資料集上以 9.39 的 FID"),
        (17, "hl-evidence", "使用者偏好研究也證實評估者更偏好我們的修補結果"),
        (17, "hl-thesis", "LDM 框架在多樣影像合成任務上的多功能性"),
        # Para 19 (conclusion)
        (19, "hl-thesis", "在感知壓縮階段與生成建模之間明確分離"),
        (19, "hl-thesis", "大幅降低擴散模型的計算負擔"),
        (19, "hl-evidence", "在多項基準上實現了與或超越像素空間擴散模型的結果"),
    ],

    "mae.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "遮罩自編碼器（MAE）"),
        (0, "hl-method", "隨機遮罩輸入影像的 patch，然後重建缺失的像素"),
        (0, "hl-thesis", "高遮罩比例（如 75%）同時產生了有意義的自監督任務與高效的訓練"),
        (0, "hl-evidence", "ViT-Huge 達到了 87.8% 的 ImageNet-1K 精確度"),
        # Para 2
        (1, "hl-concept", "自監督學習"),
        (1, "hl-thesis", "NLP 中 GPT 與 BERT 等模型已展示自監督預訓練的巨大成功"),
        (1, "hl-rebuttal", "電腦視覺中自監督方法與 NLP 之間的差距仍然存在"),
        # Para 3
        (2, "hl-thesis", "是什麼使得遮罩自編碼在視覺與語言之間產生差異？"),
        (2, "hl-method", "架構差異"),
        (2, "hl-method", "資訊密度差異"),
        (2, "hl-method", "解碼器角色差異"),
        # Para 4
        (3, "hl-concept", "架構差異"),
        (3, "hl-method", "ViT 的問世改變了這一格局"),
        # Para 5
        (4, "hl-concept", "資訊密度"),
        (4, "hl-thesis", "影像具有大量的空間冗餘"),
        (4, "hl-method", "高遮罩比例"),
        # Para 6
        (5, "hl-concept", "解碼器"),
        (5, "hl-thesis", "在視覺中解碼器重建的是像素"),
        # Para 7 (related)
        (6, "hl-concept", "BERT"),
        (6, "hl-concept", "GPT"),
        (6, "hl-concept", "BEiT"),
        (6, "hl-concept", "iGPT"),
        # Para 8 (encoder)
        # 已處理
        # Para 9 (decoder)
        # 已處理
        # Para 10 (masking)
        (9, "hl-method", "隨機取樣策略"),
        (9, "hl-method", "均勻隨機取樣"),
        (9, "hl-thesis", "消除潛在的中心偏差"),
        # Para 11 (target)
        (10, "hl-method", "像素重建"),
        (10, "hl-method", "MSE 損失"),
        (10, "hl-method", "patch 正規化"),
        # Para 12 (results)
        # 已處理
        # Para 13 (decoder)
        (12, "hl-method", "極淺的解碼器"),
        (12, "hl-evidence", "單一 Transformer 區塊的解碼器即可達到 84.8% 的精確度"),
        # Para 14 (reconstruction target)
        (13, "hl-method", "像素重建"),
        (13, "hl-evidence", "像素重建優於 tokenized 目標"),
        # Para 15 (augmentation)
        (14, "hl-method", "僅使用裁切與水平翻轉"),
        (14, "hl-thesis", "MAE 對資料增強的依賴性極低"),
        # Para 16 (scaling)
        (15, "hl-evidence", "ViT-Large 達到 85.9%"),
        (15, "hl-evidence", "ViT-Huge 達到 86.9%"),
        (15, "hl-thesis", "MAE 對更大模型的擴展效果優異"),
        # Para 17 (transfer)
        (16, "hl-evidence", "在 COCO 物件偵測上達到 53.3 APbox"),
        (16, "hl-evidence", "在 ADE20K 語意分割上達到 51.5 mIoU"),
        # Para 18 (vs supervised)
        (17, "hl-evidence", "MAE 預訓練超越了所有監督式預訓練"),
        (17, "hl-thesis", "自監督預訓練可以超越監督式預訓練"),
        # Para 19 (conclusion)
        (18, "hl-thesis", "簡單的遮罩與重建方法可以作為強大的視覺表示學習手段"),
        (18, "hl-thesis", "高遮罩比例既產生有意義的任務也實現高效訓練"),
        (19, "hl-evidence", "在 ImageNet-1K 上達到 87.8% 的精確度"),
    ],

    "mask2former.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "Mask2Former"),
        (0, "hl-thesis", "統一分割架構"),
        (0, "hl-method", "遮罩注意力"),
        (0, "hl-evidence", "在全景、實例與語意分割三項任務上均超越專門化架構"),
        # Para 2
        (1, "hl-concept", "MaskFormer"),
        (1, "hl-thesis", "以遮罩分類取代逐像素分類"),
        (1, "hl-rebuttal", "在實例分割上仍落後於專門化方法"),
        (1, "hl-method", "Mask2Former 透過改進 Transformer 解碼器來縮小差距"),
        # Para 3
        (2, "hl-concept", "語意分割"),
        (2, "hl-method", "逐像素分類"),
        (2, "hl-concept", "實例分割"),
        (2, "hl-concept", "Mask R-CNN"),
        # Para 4-6
        (3, "hl-concept", "全景分割"),
        # 已部分處理
        (3, "hl-concept", "端對端全景分割"),
        # Para 5 (architecture)
        (4, "hl-method", "遮罩注意力"),
        (4, "hl-method", "將交叉注意力限制在前景區域"),
        (4, "hl-thesis", "加速收斂並提升效能"),
        # Para 6 (efficient)
        (5, "hl-method", "高效多尺度策略"),
        (5, "hl-method", "僅在最高解析度特徵上使用 Transformer 解碼器"),
        # Para 7 (masked attention) - 已部分處理
        (6, "hl-method", "以預測的遮罩約束交叉注意力"),
        (6, "hl-thesis", "與標準交叉注意力相比，收斂速度快 3 倍"),
        # Para 8 (multi-scale)
        (7, "hl-method", "多解析度特徵饋入逐層 Transformer 解碼器"),
        (7, "hl-method", "循環式高到低解析度順序"),
        # Para 9 (optimization)
        (8, "hl-method", "可學習查詢特徵的優化改進"),
        (8, "hl-method", "去除 dropout"),
        (8, "hl-method", "在查詢上使用監督訊號"),
        # Para 10-16 results...
        (9, "hl-evidence", "在全景分割上以 57.8 PQ 超越所有現有方法"),
        (10, "hl-evidence", "在實例分割上以 50.1 AP 超越 Mask R-CNN 與 HTC++"),
        (11, "hl-evidence", "在語意分割上以 57.7 mIoU 建立新的最先進水準"),
        # Para 12 (ablation masked attention)
        (12, "hl-evidence", "遮罩注意力帶來 +3.6 AP 的提升"),
        (12, "hl-evidence", "收斂速度比標準交叉注意力快 3 倍"),
        # Para 13 (multi-scale ablation)
        (13, "hl-evidence", "多尺度策略帶來 +1.1 AP 的提升"),
        # Para 14-19 more results and conclusion
    ],

    "minimalproblems.html": [
        # Para 1 (abstract)
        (0, "hl-method", "基於學習的方法"),
        (0, "hl-method", "同倫延拓"),
        (0, "hl-method", "學習式分類器"),
        (0, "hl-evidence", "低於 70 微秒的求解時間"),
        (0, "hl-evidence", "超過 10 倍的加速"),
        # Para 2
        (1, "hl-method", "先抽取對應點的最小樣本，求解編碼幾何約束的多項式系統"),
        (1, "hl-thesis", "最小求解器的速度成為關鍵瓶頸"),
        (1, "hl-rebuttal", "難度高出數個數量級"),
        # Para 3 (related)
        (4, "hl-concept", "Nister 的五點演算法"),
        (4, "hl-method", "作用矩陣技術"),
        (4, "hl-method", "自動生成框架"),
        (4, "hl-rebuttal", "特徵值計算在模板規模上的三次方增長"),
        # Para 6 (formulation) - 已部分處理
        (7, "hl-method", "參數化多項式系統"),
        (7, "hl-concept", "光滑流形 M"),
        (7, "hl-evidence", "一般性複數解的數量為 80 個"),
        # Para 7 (homotopy)
        (8, "hl-method", "同倫延拓"),
        (8, "hl-method", "從已知起始解追蹤至目標解"),
        # Para 8 (anchor selection)
        (9, "hl-method", "錨點選擇"),
        (9, "hl-method", "學習式分類器"),
        (9, "hl-thesis", "選取收斂至真實解的起始對"),
        # Para 9 (path tracking)
        (10, "hl-method", "路徑追蹤"),
        (10, "hl-method", "歐拉預測與牛頓修正"),
        # Para 10-13 results
        (13, "hl-evidence", "在 Scranton 問題上達到 67 微秒"),
        (13, "hl-evidence", "相較於 HC 管線加速 10 倍以上"),
    ],

    "pointnerf.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "Point-NeRF"),
        (0, "hl-method", "使用神經三維點雲搭配相關的神經特徵來建模體積輻射場"),
        (0, "hl-thesis", "結合基於點雲的經典表示與體積神經渲染的優勢"),
        (0, "hl-evidence", "僅需 20-40 分鐘的微調即可達成超越 NeRF 的品質"),
        # Para 2 (NeRF intro)
        (1, "hl-concept", "NeRF"),
        (1, "hl-method", "以 MLP 表示連續的輻射場"),
        (1, "hl-rebuttal", "需要數十小時的逐場景最佳化"),
        (1, "hl-thesis", "Point-NeRF 透過預訓練的深度網路實現快速初始化"),
        # Para 3
        (2, "hl-concept", "直接網路推論"),
        (2, "hl-method", "從輸入影像直接預測初始點雲與神經特徵"),
        (2, "hl-evidence", "每個場景僅需約 25 分鐘的微調"),
        # Para 5 (related - MVS)
        (4, "hl-concept", "運動恢復結構（SfM）"),
        (4, "hl-concept", "多視圖立體匹配（MVS）"),
        (4, "hl-method", "基於點雲的神經渲染"),
        (4, "hl-thesis", "我們基於點雲的方法使用三維體積渲染"),
        # Para 6 (related - NeRF) - 已部分處理
        (5, "hl-concept", "動態場景捕捉、重新打光、外觀編輯"),
        # Para 7 (volume rendering)
        (6, "hl-method", "可微分的光線步進"),
        (6, "hl-method", "體積密度來累積輻射值"),
        # Para 8 (point representation)
        (7, "hl-method", "K 個最近鄰神經點"),
        (7, "hl-method", "逆距離加權"),
        (7, "hl-method", "MLP 處理聚合後的特徵"),
        # Para 9 (generation)
        (8, "hl-method", "深度預測網路"),
        (8, "hl-method", "2D CNN 特徵提取"),
        # Para 10-13 (training)
        (9, "hl-method", "逐場景微調"),
        (9, "hl-method", "點雲增長與修剪"),
        # Para 14 (results DTU)
        (13, "hl-evidence", "在 DTU 資料集上達到 26.44 dB PSNR"),
        (14, "hl-evidence", "在 NeRF Synthetic 上達到 30.97 dB PSNR"),
        # Para 18-20 (conclusion)
        (19, "hl-thesis", "透過直接網路推論實現快速高品質的初始化"),
        (19, "hl-thesis", "大幅縮短逐場景最佳化的時間"),
    ],

    "refnerf.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "Ref-NeRF"),
        (0, "hl-method", "以反射輻射取代 NeRF 的外觀參數化"),
        (0, "hl-method", "法向量正則化"),
        (0, "hl-thesis", "改善光澤表面的渲染品質"),
        (0, "hl-evidence", "達到最先進的渲染品質"),
        # Para 2 (intro)
        (1, "hl-rebuttal", "鏡面高光附近隨觀看方向快速變化"),
        (1, "hl-rebuttal", "對新視角下光澤外觀的插值效果很差"),
        # Para 3 (reflected radiance)
        (2, "hl-method", "反射輻射方向"),
        (2, "hl-method", "以估計的法向量反射觀看方向"),
        (2, "hl-thesis", "反射輻射隨觀看方向的變化遠比發射輻射平滑"),
        # Para 4 (IDE)
        (3, "hl-method", "整合方向編碼（IDE）"),
        (3, "hl-method", "以 vMF 分佈建模反射方向的不確定性"),
        (3, "hl-thesis", "粗糙表面產生較寬的瓣，光滑表面產生較窄的瓣"),
        # Para 5 (normal regularization)
        (4, "hl-method", "法向量正則化"),
        (4, "hl-method", "將預測法向量對齊密度梯度方向"),
        (4, "hl-method", "背面懲罰"),
        # Para 6 (diffuse + specular)
        (5, "hl-method", "漫反射與鏡面分離"),
        (5, "hl-method", "瓶頸 MLP"),
        # Para 7-10 (related)
        (6, "hl-concept", "NeRF"),
        (6, "hl-concept", "Mip-NeRF"),
        # Para 11-14 (experiments)
        (10, "hl-evidence", "在 Shiny Blender 上達到最先進的 PSNR"),
        (10, "hl-evidence", "在反射場景上顯著優於 NeRF 與 Mip-NeRF"),
        # Para 15-16 (ablation)
        (14, "hl-evidence", "IDE 帶來最大的品質提升"),
        (14, "hl-evidence", "法向量正則化改善了幾何品質"),
        # Para 17-19 (conclusion)
        (19, "hl-thesis", "結構化的反射輻射表示顯著改善了光澤場景的渲染"),
        (19, "hl-thesis", "IDE 編碼和法向量正則化的組合是關鍵"),
        (20, "hl-evidence", "達到最先進的渲染品質"),
        (20, "hl-thesis", "可解釋的內部表示使場景編輯成為可能"),
    ],

    "restormer.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "Restormer"),
        (0, "hl-method", "多 Dconv 頭轉置注意力"),
        (0, "hl-method", "門控 Dconv 前饋網路"),
        (0, "hl-thesis", "使 Transformer 能高效處理高解析度影像修復"),
        (0, "hl-evidence", "在多項影像修復任務上達到最先進的效能"),
        # Para 2 - 已處理
        # Para 3 (CNN limitations)
        (2, "hl-rebuttal", "受限的感受野使其無法建模長距離依賴關係"),
        (2, "hl-rebuttal", "靜態濾波器權重無法靈活適應輸入內容"),
        # Para 4 (Transformer for restoration)
        (3, "hl-concept", "Transformer"),
        (3, "hl-thesis", "自注意力機制能建模長距離像素互動"),
        (3, "hl-rebuttal", "計算量隨空間解析度呈二次方增長"),
        # Para 5 (related - prior)
        (4, "hl-concept", "IPT"),
        (4, "hl-concept", "SwinIR"),
        (4, "hl-method", "在小型影像區塊上施加自注意力"),
        (4, "hl-rebuttal", "犧牲了 Transformer 的全域建模優勢"),
        # Para 6 (MDTA) - 已部分處理
        (5, "hl-method", "在通道維度而非空間維度上施加注意力"),
        (5, "hl-thesis", "達到線性複雜度"),
        # Para 7 (GDFN)
        (6, "hl-method", "門控機制"),
        (6, "hl-method", "深度摺積"),
        (6, "hl-thesis", "控制資訊流動並編碼局部結構"),
        # Para 8 (progressive)
        (7, "hl-method", "漸進式學習"),
        (7, "hl-method", "初期使用較大的 patch，後期減小 patch 大小"),
        # Para 9-10 (MDTA detail)
        (8, "hl-method", "深度摺積生成查詢、鍵、值"),
        (8, "hl-method", "1x1 摺積接深度 3x3 摺積"),
        # Para 10 (MDTA detail continued) - 已處理
        # Para 11 (GDFN detail) - 已處理
        # Para 12-15 (results)
        (11, "hl-evidence", "在影像去噪上達到最先進的 PSNR"),
        (12, "hl-evidence", "在去雨上達到最先進的 PSNR"),
        (12, "hl-evidence", "在去模糊上達到最先進的 PSNR"),
        # Para 16 (ablation)
        (15, "hl-evidence", "MDTA 比空間注意力更高效"),
        (15, "hl-evidence", "GDFN 比標準 FFN 提升 0.12 dB"),
        # Para 17-19 (conclusion)
        (18, "hl-thesis", "轉置注意力在通道維度上施加是處理高解析度影像的有效策略"),
        (18, "hl-thesis", "門控前饋網路的局部結構建模與標準 FFN 互補"),
    ],

    "swinv2.html": [
        # Para 1 (abstract)
        (0, "hl-concept", "Swin Transformer V2"),
        (0, "hl-method", "殘差後正規化"),
        (0, "hl-method", "餘弦注意力"),
        (0, "hl-method", "對數空間連續位置偏置"),
        (0, "hl-evidence", "訓練了 30 億參數的模型"),
        (0, "hl-evidence", "在四項代表性基準上達到最先進的效能"),
        # Para 2 (scaling challenge)
        (1, "hl-thesis", "訓練不穩定性"),
        (1, "hl-thesis", "視窗解析度跨越訓練與測試的差距"),
        (1, "hl-thesis", "對大量標註資料的飢渴"),
        # Para 3 (language scaling)
        (2, "hl-evidence", "語言模型已擴展至數千億參數"),
        (2, "hl-concept", "GPT-3"),
        (2, "hl-evidence", "1750 億參數"),
        # Para 4 (vision scaling)  - 已部分處理
        (3, "hl-rebuttal", "現有的大型視覺模型僅被應用於影像分類任務"),
        # Para 5 (instability)
        (4, "hl-method", "殘差後正規化"),
        (4, "hl-method", "餘弦注意力"),
        (4, "hl-thesis", "解決訓練不穩定性"),
        # Para 6 (cosine attention)
        (5, "hl-method", "餘弦注意力"),
        (5, "hl-thesis", "注意力權重的計算不受幅度影響"),
        (5, "hl-method", "可學習的溫度參數"),
        # Para 7 (post-norm) - 已部分處理
        (6, "hl-method", "殘差後正規化"),
        (6, "hl-thesis", "層輸出的幅值在深度上保持穩定"),
        # Para 8 (log-CPB)
        (7, "hl-method", "對數空間連續位置偏置"),
        (7, "hl-thesis", "實現跨視窗解析度的平順遷移"),
        # Para 9 (SimMIM)
        (8, "hl-method", "SimMIM 自監督預訓練"),
        (8, "hl-thesis", "減少對大量標註資料的依賴"),
        # Para 10-14 (results)
        (12, "hl-evidence", "在 ImageNet-V2 上達到 84.0% top-1 精確度"),
        (13, "hl-evidence", "在 COCO 物件偵測上達到 63.1 APbox"),
        (13, "hl-evidence", "在 ADE20K 語意分割上達到 59.9 mIoU"),
        (14, "hl-evidence", "在 Kinetics-400 上達到 86.8% top-1 精確度"),
        # Para 15-19 (ablation & conclusion)
        (17, "hl-evidence", "餘弦注意力相較於點積注意力提升了訓練穩定性"),
        (17, "hl-evidence", "殘差後正規化進一步改善了收斂"),
        # Para 20-22 (conclusion)
        (21, "hl-thesis", "解決了將 Swin Transformer 擴展至數十億參數時的三個關鍵挑戰"),
        (21, "hl-thesis", "餘弦注意力、殘差後正規化與對數空間 CPB 的組合"),
        (22, "hl-evidence", "30 億參數的 SwinV2-G 在四項基準上達到最先進的效能"),
    ],
}


def is_inside_hl_span(text, pos):
    """檢查 pos 是否在 hl- span 內"""
    preceding = text[:pos]
    opens = len(re.findall(r'<span\s+class="hl-(?:thesis|concept|evidence|rebuttal|method)">', preceding))
    closes = len(re.findall(r'</span>', preceding))
    return opens > closes


def is_inside_html_tag(text, pos):
    """檢查 pos 是否在 HTML 標籤內"""
    last_open = text.rfind('<', 0, pos)
    last_close = text.rfind('>', 0, pos)
    if last_open == -1:
        return False
    return last_open > last_close


def wrap_in_zh(zh_html, term, hl_class):
    """在 zh_html 中找到 term 並加上 hl-class，回傳 (新HTML, 是否修改)"""
    idx = 0
    while True:
        pos = zh_html.find(term, idx)
        if pos == -1:
            return zh_html, False

        # 跳過已在 HTML 標籤或 hl-span 內的
        if is_inside_html_tag(zh_html, pos) or is_inside_hl_span(zh_html, pos):
            idx = pos + 1
            continue

        # 包裹
        new = zh_html[:pos] + f'<span class="{hl_class}">{term}</span>' + zh_html[pos + len(term):]
        return new, True

    return zh_html, False


def process_file(filepath, fixes):
    """根據手動修補表處理單個檔案"""
    filename = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"處理：{filename}")
    print(f"{'='*60}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    zh_pattern = r'<div\s+class="zh-text">(.*?)</div>'
    zh_matches = list(re.finditer(zh_pattern, content, re.DOTALL))

    total_changes = 0
    replacements = []

    for para_idx, hl_class, zh_term in fixes:
        if para_idx >= len(zh_matches):
            print(f"  警告：段落索引 {para_idx} 超出範圍（共 {len(zh_matches)} 段）")
            continue

        zh_match = zh_matches[para_idx]
        zh_html = zh_match.group(1)
        zh_start = zh_match.start(1)
        zh_end = zh_match.end(1)

        # 檢查 term 是否在純文字中
        zh_plain = get_plain_text(zh_html)
        if zh_term not in zh_plain:
            # 嘗試容錯搜尋（可能有微小差異）
            continue

        # 檢查是否已有此高亮
        escaped = re.escape(zh_term)
        already = rf'<span\s+class="{re.escape(hl_class)}">[^<]*?{escaped}'
        if re.search(already, zh_html):
            continue

        # 檢查是否被其他 hl- 包裹
        any_hl = rf'<span\s+class="hl-[^"]*">[^<]*?{escaped}'
        if re.search(any_hl, zh_html):
            continue

        new_zh, changed = wrap_in_zh(zh_html, zh_term, hl_class)
        if changed:
            replacements.append((zh_start, zh_end, zh_match.group(1), new_zh, para_idx))
            # 更新 zh_matches 中的內容以避免同段落多次修改時的衝突
            # 重新讀取（因為後面的修改會改變位置）
            total_changes += 1

    # 從後往前替換，但需注意同一段落有多次修改
    # 先按段落分組
    para_groups = {}
    for zh_start, zh_end, old_zh, new_zh, para_idx in replacements:
        if para_idx not in para_groups:
            para_groups[para_idx] = []
        para_groups[para_idx].append((zh_start, zh_end, old_zh, new_zh))

    # 對每個段落，依次應用所有修改
    # 需要重新處理：在同一段落中累積修改
    final_replacements = []
    for para_idx in sorted(para_groups.keys()):
        group = para_groups[para_idx]
        zh_match = zh_matches[para_idx]
        current_zh = zh_match.group(1)

        for _, _, _, new_zh in group:
            # 這裡 new_zh 是基於原始 zh_html 計算的，但我們需要累積
            pass

    # 更簡單的方法：直接重新處理每個段落
    content_new = content
    for para_idx in sorted(para_groups.keys(), reverse=True):
        zh_match = zh_matches[para_idx]
        zh_html = zh_match.group(1)
        zh_start = zh_match.start(1)
        zh_end = zh_match.end(1)

        # 取得此段落的所有修補
        para_fixes = [(hl_class, zh_term) for p_idx, hl_class, zh_term in fixes if p_idx == para_idx]

        modified = zh_html
        para_changes = 0
        for hl_class, zh_term in para_fixes:
            zh_plain = get_plain_text(modified)
            if zh_term not in zh_plain:
                continue

            escaped = re.escape(zh_term)
            already = rf'<span\s+class="{re.escape(hl_class)}">[^<]*?{escaped}'
            if re.search(already, modified):
                continue
            any_hl = rf'<span\s+class="hl-[^"]*">[^<]*?{escaped}'
            if re.search(any_hl, modified):
                continue

            new_mod, changed = wrap_in_zh(modified, zh_term, hl_class)
            if changed:
                modified = new_mod
                para_changes += 1

        if para_changes > 0:
            content_new = content_new[:zh_start] + modified + content_new[zh_end:]
            print(f"  段落 {para_idx + 1}: 新增 {para_changes} 個高亮")
            total_changes += para_changes - len(para_groups[para_idx])  # 修正計數

    if total_changes > 0 or any(para_groups.values()):
        actual_changes = sum(1 for _ in re.finditer(r'<span class="hl-', content_new)) - sum(1 for _ in re.finditer(r'<span class="hl-', content))
        if actual_changes > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content_new)
            print(f"  總計新增 {actual_changes} 個高亮，已寫入。")
        else:
            print(f"  無新增高亮。")
    else:
        print(f"  無需修補。")


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cvpr", "2022")

    for filename, fixes in MANUAL_FIXES.items():
        if not fixes:
            print(f"\n{filename}: 跳過（無修補項目）")
            continue
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            process_file(filepath, fixes)
        else:
            print(f"\n警告：{filepath} 不存在")


if __name__ == "__main__":
    main()
