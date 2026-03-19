"""
擷取 CvHub 論文之間的引用關係，產生 citations.json。
掃描全部論文 HTML 的文字內容，比對其他論文的名稱/縮寫，建立引用邊。
"""
import os
import re
import json
import html as html_module
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ===== 論文引用名稱資料庫 =====
# key: 論文路徑 (不含 .html)
# value: list of (keyword, case_sensitive) tuples
# 未列入的論文會自動從檔名推導

CITATION_NAMES = {
    # ===== Classics =====
    "classics/resnet": ["ResNet", "ResNet-50", "ResNet-101", "ResNet-152"],
    "classics/yolo": ["YOLO"],
    "classics/vit": ["ViT", "Vision Transformer"],
    "classics/ddpm": ["DDPM", "Denoising Diffusion Probabilistic"],
    "classics/transformer": [],  # "Transformer" 太常見，不搜尋

    # ===== CVPR 2013 =====
    "cvpr/2013/otb": ["OTB"],

    # ===== CVPR 2014 =====
    "cvpr/2014/rcnn": ["R-CNN"],
    "cvpr/2014/caffe": ["Caffe"],
    "cvpr/2014/deepface": ["DeepFace"],
    "cvpr/2014/deepid": ["DeepID"],
    "cvpr/2014/mcg": ["MCG"],

    # ===== CVPR 2015 =====
    "cvpr/2015/facenet": ["FaceNet"],
    "cvpr/2015/fcn": ["Fully Convolutional Network"],
    "cvpr/2015/googlenet": ["GoogLeNet", "Inception"],
    "cvpr/2015/dynamicfusion": ["DynamicFusion"],
    "cvpr/2015/lrcn": ["LRCN"],
    "cvpr/2015/showandtell": ["Show and Tell"],
    "cvpr/2015/shapenets": ["ShapeNet", "3D ShapeNets"],
    "cvpr/2015/hypercolumns": ["Hypercolumn"],

    # ===== CVPR 2016 =====
    "cvpr/2016/cam": ["Class Activation Map"],
    "cvpr/2016/contextencoder": ["Context Encoder"],
    "cvpr/2016/inceptionv3": ["Inception-v3", "Inception v3", "InceptionV3", "BN-Inception"],
    "cvpr/2016/ohem": ["OHEM"],
    "cvpr/2016/nturgbd": ["NTU RGB+D", "NTU-RGBD"],
    "cvpr/2016/stackedattn": ["Stacked Attention Network"],

    # ===== CVPR 2017 =====
    "cvpr/2017/fpn": ["FPN", "Feature Pyramid Network"],
    "cvpr/2017/pointnet": ["PointNet"],
    "cvpr/2017/densenet": ["DenseNet"],
    "cvpr/2017/pix2pix": ["pix2pix"],
    "cvpr/2017/openpose": ["OpenPose"],
    "cvpr/2017/pspnet": ["PSPNet"],
    "cvpr/2017/deformconv": ["Deformable Convolution", "DCN", "deformable conv"],
    "cvpr/2017/resnext": ["ResNeXt"],
    "cvpr/2017/srgan": ["SRGAN"],
    "cvpr/2017/polygonrnn": ["Polygon-RNN", "PolygonRNN"],
    "cvpr/2017/simgan": ["SimGAN"],

    # ===== CVPR 2018 =====
    "cvpr/2018/mobilenetv2": ["MobileNetV2", "MobileNet v2", "MobileNet"],
    "cvpr/2018/nonlocal": ["Non-local", "Non-Local", "non-local neural network"],
    "cvpr/2018/senet": ["SENet", "SE-Net", "Squeeze-and-Excitation", "SE block"],
    "cvpr/2018/stargan": ["StarGAN"],
    "cvpr/2018/progan": ["ProGAN", "Progressive GAN"],
    "cvpr/2018/pix2pixhd": ["pix2pixHD"],
    "cvpr/2018/densepose": ["DensePose"],
    "cvpr/2018/r21d": ["R(2+1)D"],
    "cvpr/2018/splatnet": ["SPLATNet"],
    "cvpr/2018/taskonomy": ["Taskonomy"],

    # ===== CVPR 2019 =====
    "cvpr/2019/arcface": ["ArcFace"],
    "cvpr/2019/stylegan": ["StyleGAN"],
    "cvpr/2019/deepsdf": ["DeepSDF"],
    "cvpr/2019/spade": ["SPADE"],
    "cvpr/2019/pointrcnn": ["PointRCNN"],
    "cvpr/2019/siammask": ["SiamMask"],
    "cvpr/2019/bagoftricks": ["Bag of Tricks"],
    "cvpr/2019/giou": ["GIoU"],
    "cvpr/2019/autodeeplab": ["Auto-DeepLab"],
    "cvpr/2019/ganfit": ["GANFit"],

    # ===== CVPR 2020 =====
    "cvpr/2020/moco": ["MoCo", "Momentum Contrast"],
    "cvpr/2020/efficientdet": ["EfficientDet"],
    "cvpr/2020/pointrend": ["PointRend"],
    "cvpr/2020/higherhrnet": ["HigherHRNet", "HRNet"],
    "cvpr/2020/pifuhd": ["PIFuHD", "PIFu"],
    "cvpr/2020/circleloss": ["Circle Loss"],
    "cvpr/2020/x3d": ["X3D"],
    "cvpr/2020/alae": ["ALAE"],
    "cvpr/2020/bspnet": ["BSP-Net", "BSPNet"],

    # ===== CVPR 2021 =====
    "cvpr/2021/repvgg": ["RepVGG"],
    "cvpr/2021/setr": ["SETR"],
    "cvpr/2021/simsiam": ["SimSiam"],
    "cvpr/2021/dnerf": ["D-NeRF"],
    "cvpr/2021/nerfw": ["NeRF-W", "NeRF in the Wild"],
    "cvpr/2021/vistr": ["VisTR"],
    "cvpr/2021/updetr": ["UP-DETR"],
    "cvpr/2021/t2tvit": ["T2T-ViT"],
    "cvpr/2021/giraffe": ["GIRAFFE"],
    "cvpr/2021/raft3d": ["RAFT-3D"],

    # ===== CVPR 2022 =====
    "cvpr/2022/convnext": ["ConvNeXt"],
    "cvpr/2022/mae": ["Masked Autoencoder"],
    "cvpr/2022/mask2former": ["Mask2Former"],
    "cvpr/2022/ldm": ["Latent Diffusion"],
    "cvpr/2022/swinv2": ["Swin Transformer V2", "SwinV2"],
    "cvpr/2022/dndetr": ["DN-DETR"],
    "cvpr/2022/pointnerf": ["Point-NeRF"],
    "cvpr/2022/refnerf": ["Ref-NeRF"],
    "cvpr/2022/restormer": ["Restormer"],

    # ===== CVPR 2023 =====
    "cvpr/2023/dreambooth": ["DreamBooth"],
    "cvpr/2023/imagebind": ["ImageBind"],
    "cvpr/2023/eva": ["EVA-CLIP"],
    "cvpr/2023/gigagan": ["GigaGAN"],
    "cvpr/2023/maskdino": ["Mask DINO", "MaskDINO"],
    "cvpr/2023/internimage": ["InternImage"],
    "cvpr/2023/odise": ["ODISE"],
    "cvpr/2023/sjc": ["Score Jacobian"],
    "cvpr/2023/uniad": ["UniAD"],
    "cvpr/2023/dynibar": ["DynIBaR"],
    "cvpr/2023/visprog": ["VisProg"],

    # ===== CVPR 2024 =====
    "cvpr/2024/depthanything": ["Depth Anything"],
    "cvpr/2024/florence2": ["Florence-2", "Florence"],
    "cvpr/2024/efficientsam": ["EfficientSAM"],
    "cvpr/2024/yoloworld": ["YOLO-World"],
    "cvpr/2024/4dgs": ["4D Gaussian Splatting", "4DGS"],
    "cvpr/2024/bioclip": ["BioCLIP"],
    "cvpr/2024/internvl": ["InternVL"],
    "cvpr/2024/mipsplatting": ["Mip-Splatting"],
    "cvpr/2024/pixelsplat": ["pixelSplat"],
    "cvpr/2024/richhf": ["Rich Human Feedback"],

    # ===== CVPR 2025 =====
    "cvpr/2025/megasam": ["MegaSAM"],
    "cvpr/2025/mast3rslam": ["MASt3R-SLAM", "MASt3R"],
    "cvpr/2025/depthcrafter": ["DepthCrafter"],
    "cvpr/2025/vggt": ["VGGT"],
    "cvpr/2025/trellis": ["TRELLIS"],
    "cvpr/2025/omnigen": ["OmniGen"],
    "cvpr/2025/studentsplatting": ["Student Splatting"],
    "cvpr/2025/janus": ["Janus"],
    "cvpr/2025/ddtllama": ["DDT-LLaMA"],
    "cvpr/2025/molmo": ["Molmo"],

    # ===== ICCV 2013 =====
    "iccv/2013/overfeat": ["OverFeat"],

    # ===== ICCV 2015 =====
    "iccv/2015/fastrcnn": ["Fast R-CNN", "Fast RCNN", "FastRCNN"],
    "iccv/2015/flownet": ["FlowNet"],
    "iccv/2015/c3d": ["C3D"],
    "iccv/2015/hed": ["HED"],
    "iccv/2015/deconvnet": ["DeconvNet"],
    "iccv/2015/crfrnn": ["CRF-RNN", "CRF as RNN"],
    "iccv/2015/prelu": ["PReLU"],

    # ===== ICCV 2017 =====
    "iccv/2017/maskrcnn": ["Mask R-CNN", "Mask RCNN", "MaskRCNN"],
    "iccv/2017/retinanet": ["RetinaNet", "Focal Loss"],
    "iccv/2017/cyclegan": ["CycleGAN"],
    "iccv/2017/gradcam": ["Grad-CAM", "GradCAM"],
    "iccv/2017/channelpruning": ["Channel Pruning"],

    # ===== ICCV 2019 =====
    "iccv/2019/slowfast": ["SlowFast"],
    "iccv/2019/fcos": ["FCOS"],
    "iccv/2019/cutmix": ["CutMix"],
    "iccv/2019/singan": ["SinGAN"],
    "iccv/2019/cascadercnn": ["Cascade R-CNN", "Cascade RCNN"],
    "iccv/2019/meshrcnn": ["Mesh R-CNN"],
    "iccv/2019/votenet": ["VoteNet"],
    "iccv/2019/randwire": ["RandWire"],

    # ===== ICCV 2021 =====
    "iccv/2021/swin": ["Swin Transformer", "Swin"],
    "iccv/2021/maskformer": ["MaskFormer"],
    "iccv/2021/mipnerf": ["Mip-NeRF", "MipNeRF"],
    "iccv/2021/dpt": ["DPT"],
    "iccv/2021/pvt": ["PVT", "Pyramid Vision Transformer"],
    "iccv/2021/mvit": ["MViT"],
    "iccv/2021/focaltransformer": ["Focal Transformer"],

    # ===== ICCV 2023 =====
    "iccv/2023/sam": ["Segment Anything"],
    "iccv/2023/gaussiansplatting": ["3D Gaussian Splatting", "3DGS", "Gaussian Splatting"],
    "iccv/2023/controlnet": ["ControlNet"],
    "iccv/2023/dinov2": ["DINOv2", "DINO v2"],
    "iccv/2023/ipadapter": ["IP-Adapter"],
    "iccv/2023/nerfacto": ["Nerfacto"],
    "iccv/2023/lerf": ["LERF"],
    "iccv/2023/lavie": ["LaVie"],
    "iccv/2023/hqtrack": ["HQTrack"],

    # ===== ICCV 2025 =====
    "iccv/2025/sa2va": ["Sa2VA"],
    "iccv/2025/llavacot": ["LLaVA-CoT"],
    "iccv/2025/longsplat": ["LongSplat"],
    "iccv/2025/scenesplat": ["SceneSplat"],
    "iccv/2025/flowedit": ["FlowEdit"],

    # ===== ECCV 2014 =====
    "eccv/2014/sppnet": ["SPPNet", "SPP-Net", "Spatial Pyramid Pooling"],
    "eccv/2014/zfnet": ["ZFNet"],
    "eccv/2014/srcnn": ["SRCNN"],
    "eccv/2014/microsoft-coco": ["MS COCO", "Microsoft COCO", "COCO dataset"],

    # ===== ECCV 2016 =====
    "eccv/2016/ssd": ["SSD"],
    "eccv/2016/identity-mapping": ["identity mapping", "pre-activation ResNet"],
    "eccv/2016/siamfc": ["SiamFC"],
    "eccv/2016/perceptual-losses": ["perceptual loss"],
    "eccv/2016/stacked-hourglass": ["Stacked Hourglass", "Hourglass Network"],
    "eccv/2016/wide-resnet": ["Wide ResNet", "WRN", "Wide Residual Network"],
    "eccv/2016/tsn": ["Temporal Segment Network"],
    "eccv/2016/enet": ["ENet"],
    "eccv/2016/goturn": ["GOTURN"],

    # ===== ECCV 2018 =====
    "eccv/2018/cbam": ["CBAM"],
    "eccv/2018/deeplabv3plus": ["DeepLabv3+", "DeepLabV3+", "DeepLab"],
    "eccv/2018/groupnorm": ["Group Normalization", "GroupNorm", "Group Norm"],
    "eccv/2018/cornernet": ["CornerNet"],
    "eccv/2018/shufflenetv2": ["ShuffleNetV2", "ShuffleNet"],
    "eccv/2018/simple-baselines": ["Simple Baselines"],
    "eccv/2018/espnet": ["ESPNet"],

    # ===== ECCV 2020 =====
    "eccv/2020/detr": ["DETR", "Detection Transformer"],
    "eccv/2020/nerf": ["NeRF", "Neural Radiance Field"],
    "eccv/2020/raft": ["RAFT"],
    "eccv/2020/solo": ["SOLO"],
    "eccv/2020/ocrnet": ["OCRNet"],

    # ===== ECCV 2022 =====
    "eccv/2022/bevformer": ["BEVFormer"],
    "eccv/2022/tensorf": ["TensoRF"],
    "eccv/2022/maxvit": ["MaxViT"],
    "eccv/2022/davit": ["DaViT"],
    "eccv/2022/maskgit": ["MaskGIT"],
    "eccv/2022/petr": ["PETR"],

    # ===== ECCV 2024 =====
    "eccv/2024/dust3r": ["DUSt3R"],
    "eccv/2024/grounding-dino": ["Grounding DINO"],
    "eccv/2024/sapiens": ["Sapiens"],
    "eccv/2024/sea-raft": ["SEA-RAFT"],
    "eccv/2024/videomamba": ["VideoMamba"],
    "eccv/2024/concept-sliders": ["Concept Sliders"],
    "eccv/2024/lgm": ["LGM"],
    "eccv/2024/adversarial-diffusion-distillation": ["Adversarial Diffusion Distillation"],
    "eccv/2024/sit": ["SiT"],
}

# 經典論文年份（無法從路徑推導）
CLASSIC_YEARS = {
    "classics/resnet": 2015,
    "classics/yolo": 2016,
    "classics/transformer": 2017,
    "classics/vit": 2020,
    "classics/ddpm": 2020,
}

# HTML 標籤清除用正規表達式
TAG_RE = re.compile(r'<[^>]+>')
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)


def strip_html(text):
    """移除 HTML 標籤，保留純文字"""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = TAG_RE.sub(' ', text)
    text = html_module.unescape(text)
    return text


def extract_title(html_content):
    """從 HTML 中擷取 <title> 標籤的內容"""
    m = TITLE_RE.search(html_content)
    if m:
        title = m.group(1).strip()
        # 移除常見後綴
        for suffix in [' — 雙欄批注', ' - 雙欄批注', '—雙欄批注', ' — Annotated']:
            if title.endswith(suffix):
                title = title[:-len(suffix)].strip()
        return title
    return None


def get_paper_id(filepath):
    """將檔案路徑轉為論文 ID（相對路徑，不含 .html）"""
    rel = filepath.relative_to(BASE_DIR)
    return str(rel).replace('\\', '/').replace('.html', '')


def get_conference(paper_id):
    """從論文 ID 推導會議名稱"""
    parts = paper_id.split('/')
    return parts[0].upper() if parts[0] != 'classics' else 'Classics'


def get_year(paper_id):
    """從論文 ID 推導年份"""
    if paper_id in CLASSIC_YEARS:
        return CLASSIC_YEARS[paper_id]
    parts = paper_id.split('/')
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            pass
    return 0


def get_short_name(paper_id):
    """從論文 ID 推導短名稱"""
    # 如果在 CITATION_NAMES 中有定義，使用第一個
    if paper_id in CITATION_NAMES and CITATION_NAMES[paper_id]:
        return CITATION_NAMES[paper_id][0]
    # 否則從檔名推導
    filename = paper_id.split('/')[-1]
    # 將 kebab-case 轉為 Title Case
    if '-' in filename:
        return filename.replace('-', ' ').title()
    # 將 camelCase 拆分
    return filename.upper() if len(filename) <= 4 else filename.capitalize()


def build_search_patterns(citation_names):
    """為每篇論文建立搜尋正規表達式"""
    patterns = {}
    for paper_id, keywords in citation_names.items():
        if not keywords:
            continue
        compiled = []
        for kw in keywords:
            # 對每個關鍵字建立帶 word boundary 的正規表達式
            escaped = re.escape(kw)
            # 判斷是否需要 case-insensitive
            if kw == kw.upper() and len(kw) <= 5:
                # 全大寫短縮寫，case-sensitive + word boundary
                pattern = re.compile(r'\b' + escaped + r'\b')
            elif any(c.isupper() for c in kw) and any(c.islower() for c in kw):
                # 混合大小寫 (如 ResNet)，case-sensitive
                pattern = re.compile(r'\b' + escaped + r'\b')
            else:
                # 其他情況 case-insensitive
                pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
            compiled.append(pattern)
        patterns[paper_id] = compiled
    return patterns


def find_all_papers():
    """找出所有論文 HTML 檔案"""
    papers = []
    for pattern_dir in ['classics', 'cvpr', 'iccv', 'eccv']:
        base = BASE_DIR / pattern_dir
        if not base.exists():
            continue
        for html_file in base.rglob('*.html'):
            papers.append(html_file)
    return sorted(papers)


def main():
    print("=== CvHub 論文引用關係擷取工具 ===\n")

    # 1. 找出所有論文
    paper_files = find_all_papers()
    print(f"找到 {len(paper_files)} 篇論文\n")

    # 2. 讀取所有論文的 HTML 內容，擷取中繼資料
    nodes = []
    paper_texts = {}  # paper_id -> plain_text

    for filepath in paper_files:
        paper_id = get_paper_id(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  [警告] 無法讀取 {paper_id}: {e}")
            continue

        title = extract_title(content) or paper_id.split('/')[-1]
        short_name = get_short_name(paper_id)
        year = get_year(paper_id)
        conference = get_conference(paper_id)
        path = paper_id + '.html'

        nodes.append({
            "id": paper_id,
            "title": title,
            "shortName": short_name,
            "year": year,
            "conference": conference,
            "path": path,
        })

        # 擷取純文字（用於引用搜尋）
        plain_text = strip_html(content)
        paper_texts[paper_id] = plain_text

    print(f"已載入 {len(nodes)} 篇論文的中繼資料\n")

    # 3. 建立搜尋模式
    patterns = build_search_patterns(CITATION_NAMES)
    print(f"已建立 {len(patterns)} 組搜尋模式\n")

    # 4. 掃描引用關係
    edges = []
    edge_set = set()  # 用於去重

    for paper_id, text in paper_texts.items():
        for target_id, target_patterns in patterns.items():
            # 跳過自己引用自己
            if paper_id == target_id:
                continue
            # 檢查是否有任何關鍵字匹配
            for pat in target_patterns:
                if pat.search(text):
                    edge_key = (paper_id, target_id)
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": paper_id,
                            "target": target_id,
                        })
                    break  # 一找到就停止

    print(f"找到 {len(edges)} 條引用關係\n")

    # 5. 統計被引用次數最多的論文
    cite_count = {}
    for edge in edges:
        t = edge["target"]
        cite_count[t] = cite_count.get(t, 0) + 1

    print("被引用次數最多的前 20 篇論文：")
    for pid, count in sorted(cite_count.items(), key=lambda x: -x[1])[:20]:
        name = get_short_name(pid)
        print(f"  {name:25s} ({pid}) — 被引用 {count} 次")

    # 6. 輸出 JSON
    output = {
        "nodes": nodes,
        "edges": edges,
    }

    output_path = BASE_DIR / 'public' / 'citations.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n已輸出至 {output_path}")
    print(f"  節點數: {len(nodes)}")
    print(f"  邊數: {len(edges)}")


if __name__ == '__main__':
    main()
