"""
curate_github_links.py
人工修正 GitHub 連結查詢結果，並嵌入至論文 HTML。
步驟：
  1. 載入自動查詢結果（paper_github_links.json）
  2. 套用已知正確 repo 覆蓋
  3. 移除已知誤判
  4. 在論文 HTML navbar 中嵌入 GitHub 連結
用法：python scripts/curate_github_links.py [--dry-run]
"""
import os, re, json, sys
from pathlib import Path
from glob import glob

BASE = Path(r'C:\Users\alex2\Desktop\vsCode\CvHub')
INPUT_JSON = BASE / 'scripts' / 'paper_github_links.json'
OUTPUT_JSON = BASE / 'scripts' / 'paper_github_links_curated.json'

# ══════════════════════════════════════════════════════════
#  已知正確 repo（覆蓋自動查詢結果）
# ══════════════════════════════════════════════════════════
KNOWN_REPOS = {
    # ── 經典論文 ──
    'classics/resnet.html': 'https://github.com/KaimingHe/deep-residual-networks',
    'classics/yolo.html': 'https://github.com/pjreddie/darknet',
    'classics/transformer.html': 'https://github.com/tensorflow/tensor2tensor',
    'classics/vit.html': 'https://github.com/google-research/vision_transformer',
    'classics/ddpm.html': 'https://github.com/hojonathanho/diffusion',

    # ── CVPR ──
    'cvpr/2014/caffe.html': 'https://github.com/BVLC/caffe',
    'cvpr/2014/rcnn.html': 'https://github.com/rbgirshick/rcnn',
    'cvpr/2015/facenet.html': 'https://github.com/davidsandberg/facenet',
    'cvpr/2015/fcn.html': 'https://github.com/shelhamer/fcn.berkeleyvision.org',
    'cvpr/2015/googlenet.html': 'https://github.com/BVLC/caffe',  # GoogLeNet 在 Caffe Model Zoo
    'cvpr/2015/lrcn.html': 'https://github.com/LisaAnne/lisa-caffe-public',
    'cvpr/2015/showandtell.html': 'https://github.com/tensorflow/models',
    'cvpr/2015/shapenets.html': 'https://github.com/zhirongw/3DShapeNets',
    'cvpr/2016/cam.html': 'https://github.com/zhoubolei/CAM',
    'cvpr/2016/ohem.html': 'https://github.com/abhi2610/ohem',
    'cvpr/2016/contextencoder.html': 'https://github.com/pathak22/context-encoder',
    'cvpr/2017/openpose.html': 'https://github.com/CMU-Perceptual-Computing-Lab/openpose',
    'cvpr/2017/pix2pix.html': 'https://github.com/phillipi/pix2pix',
    'cvpr/2017/pointnet.html': 'https://github.com/charlesq34/pointnet',
    'cvpr/2017/pspnet.html': 'https://github.com/hszhao/PSPNet',
    'cvpr/2017/fpn.html': 'https://github.com/unsky/FPN',
    'cvpr/2017/resnext.html': 'https://github.com/facebookresearch/ResNeXt',
    'cvpr/2017/srgan.html': 'https://github.com/tensorlayer/SRGAN',
    'cvpr/2017/simgan.html': 'https://github.com/carpedm20/simulated-unsupervised-tensorflow',
    'cvpr/2017/polygonrnn.html': 'https://github.com/fidler-lab/polyrnn-pp',
    'cvpr/2018/pix2pixhd.html': 'https://github.com/NVIDIA/pix2pixHD',
    'cvpr/2018/stargan.html': 'https://github.com/yunjey/stargan',
    'cvpr/2018/senet.html': 'https://github.com/hujie-frank/SENet',
    'cvpr/2018/mobilenetv2.html': 'https://github.com/tensorflow/models',
    'cvpr/2018/taskonomy.html': 'https://github.com/StanfordVL/taskonomy',
    'cvpr/2018/splatnet.html': 'https://github.com/NVlabs/splatnet',
    'cvpr/2018/progan.html': 'https://github.com/tkarras/progressive_growing_of_gans',
    'cvpr/2018/totalcapture.html': 'https://github.com/CMU-Perceptual-Computing-Lab/openpose',
    'cvpr/2018/r21d.html': 'https://github.com/facebookresearch/VMZ',
    'cvpr/2019/stylegan.html': 'https://github.com/NVlabs/stylegan',
    'cvpr/2019/spade.html': 'https://github.com/NVlabs/SPADE',
    'cvpr/2019/pointrcnn.html': 'https://github.com/sshaoshuai/PointRCNN',
    'cvpr/2019/siammask.html': 'https://github.com/foolwood/SiamMask',
    'cvpr/2019/arcface.html': 'https://github.com/deepinsight/insightface',
    'cvpr/2019/autodeeplab.html': 'https://github.com/MenghaoGuo/AutoDeeplab',
    'cvpr/2019/ganfit.html': 'https://github.com/barisgecer/GANFit',
    'cvpr/2019/bagoftricks.html': 'https://github.com/dmlc/gluon-cv',
    'cvpr/2019/giou.html': 'https://github.com/generalized-iou/g-darknet',
    'cvpr/2020/moco.html': 'https://github.com/facebookresearch/moco',
    'cvpr/2020/pifuhd.html': 'https://github.com/facebookresearch/pifuhd',
    'cvpr/2020/higherhrnet.html': 'https://github.com/HRNet/HigherHRNet-Human-Pose-Estimation',
    'cvpr/2020/alae.html': 'https://github.com/podgorskiy/ALAE',
    'cvpr/2020/circleloss.html': 'https://github.com/TinyZeaMays/CircleLoss',
    'cvpr/2020/pointrend.html': 'https://github.com/facebookresearch/detectron2',
    'cvpr/2020/3dphoto.html': 'https://github.com/vt-vl-lab/3d-photo-inpainting',
    'cvpr/2021/giraffe.html': 'https://github.com/autonomousvision/giraffe',
    'cvpr/2021/simsiam.html': 'https://github.com/facebookresearch/simsiam',
    'cvpr/2021/repvgg.html': 'https://github.com/DingXiaoH/RepVGG',
    'cvpr/2021/setr.html': 'https://github.com/fudan-zvg/SETR',
    'cvpr/2021/vistr.html': 'https://github.com/Epiphqny/VisTR',
    'cvpr/2021/bgmatting.html': 'https://github.com/PeterL1n/BackgroundMattingV2',
    'cvpr/2021/updetr.html': 'https://github.com/dddzg/up-detr',
    'cvpr/2021/t2tvit.html': 'https://github.com/yitu-opensource/T2T-ViT',
    'cvpr/2021/raft3d.html': 'https://github.com/princeton-vl/RAFT-3D',
    'cvpr/2022/mae.html': 'https://github.com/facebookresearch/mae',
    'cvpr/2022/convnext.html': 'https://github.com/facebookresearch/ConvNeXt',
    'cvpr/2022/mask2former.html': 'https://github.com/facebookresearch/Mask2Former',
    'cvpr/2022/restormer.html': 'https://github.com/swz30/Restormer',
    'cvpr/2022/pointnerf.html': 'https://github.com/Xharlie/pointnerf',
    'cvpr/2022/ldm.html': 'https://github.com/CompVis/latent-diffusion',
    'cvpr/2022/refnerf.html': 'https://github.com/google-research/multinerf',
    'cvpr/2022/swinv2.html': 'https://github.com/microsoft/Swin-Transformer',
    'cvpr/2023/odise.html': 'https://github.com/NVlabs/ODISE',
    'cvpr/2023/maskdino.html': 'https://github.com/IDEA-Research/MaskDINO',
    'cvpr/2023/uniad.html': 'https://github.com/OpenDriveLab/UniAD',
    'cvpr/2023/visprog.html': 'https://github.com/allenai/visprog',
    'cvpr/2023/gigagan.html': 'https://github.com/mingukkang/GigaGAN',
    'cvpr/2023/sjc.html': 'https://github.com/pals-ttic/sjc',
    'cvpr/2023/internimage.html': 'https://github.com/OpenGVLab/InternImage',
    'cvpr/2024/pixelsplat.html': 'https://github.com/dcharatan/pixelsplat',
    'cvpr/2024/bioclip.html': 'https://github.com/Imageomics/bioclip',
    'cvpr/2024/florence2.html': 'https://github.com/microsoft/Florence-2',
    'cvpr/2024/yoloworld.html': 'https://github.com/AILab-CVC/YOLO-World',
    'cvpr/2024/4dgs.html': 'https://github.com/hustvl/4DGaussians',
    'cvpr/2024/richhf.html': 'https://github.com/google-research/google-research',
    'cvpr/2025/vggt.html': 'https://github.com/facebookresearch/vggt',
    'cvpr/2025/janus.html': 'https://github.com/deepseek-ai/Janus',
    'cvpr/2025/omnigen.html': 'https://github.com/VectorSpaceLab/OmniGen',
    'cvpr/2025/trellis.html': 'https://github.com/microsoft/TRELLIS',
    'cvpr/2025/megasam.html': 'https://github.com/mega-sam/mega-sam',
    'cvpr/2025/molmo.html': 'https://github.com/allenai/molmo',
    'cvpr/2025/mast3rslam.html': 'https://github.com/rmurai0610/MASt3R-SLAM',
    'cvpr/2025/studentsplatting.html': 'https://github.com/realcrane/3D-student-splatting-and-scooping',

    # ── ECCV ──
    'eccv/2014/lsd-slam.html': 'https://github.com/tum-vision/lsd_slam',
    'eccv/2014/sppnet.html': 'https://github.com/ShaoqingRen/SPP_net',
    'eccv/2014/srcnn.html': 'https://github.com/yjn870/SRCNN-pytorch',
    'eccv/2014/zfnet.html': 'https://github.com/amir-saniyan/ZFNet',
    'eccv/2016/colorization.html': 'https://github.com/richzhang/colorization',
    'eccv/2016/ssd.html': 'https://github.com/weiliu89/caffe',
    'eccv/2016/siamfc.html': 'https://github.com/bertinetto/siamese-fc',
    'eccv/2016/goturn.html': 'https://github.com/davheld/GOTURN',
    'eccv/2016/stacked-hourglass.html': 'https://github.com/umich-vl/pose-hg-demo',
    'eccv/2016/tsn.html': 'https://github.com/yjxiong/temporal-segment-networks',
    'eccv/2016/bilateral-solver.html': 'https://github.com/poolio/bilateral_solver',
    'eccv/2016/wide-resnet.html': 'https://github.com/szagoruyko/wide-residual-networks',
    'eccv/2016/perceptual-losses.html': 'https://github.com/jcjohnson/fast-neural-style',
    'eccv/2016/identity-mapping.html': 'https://github.com/KaimingHe/resnet-1k-layers',
    'eccv/2018/cornernet.html': 'https://github.com/princeton-vl/CornerNet',
    'eccv/2018/ganimation.html': 'https://github.com/albertpumarola/GANimation',
    'eccv/2018/cbam.html': 'https://github.com/Jongchan/attention-module',
    'eccv/2018/shufflenetv2.html': 'https://github.com/megvii-model/ShuffleNet-Series',
    'eccv/2018/groupnorm.html': 'https://github.com/facebookresearch/Detectron',
    'eccv/2018/simple-baselines.html': 'https://github.com/microsoft/human-pose-estimation.pytorch',
    'eccv/2018/personlab.html': 'https://github.com/scnuhealthy/Tensorflow_PersonLab',
    'eccv/2020/raft.html': 'https://github.com/princeton-vl/RAFT',
    'eccv/2020/solo.html': 'https://github.com/WXinlong/SOLO',
    'eccv/2020/pointcontrast.html': 'https://github.com/facebookresearch/PointContrast',
    'eccv/2020/rethinking-bottleneck.html': 'https://github.com/zhoudaquan/rethinking_bottleneck_design',
    'eccv/2020/rewriting-gan.html': 'https://github.com/davidbau/rewriting',
    'eccv/2020/streaming.html': None,  # 移除誤判，無明確對應 repo
    'eccv/2022/tensorf.html': 'https://github.com/apchenstu/TensoRF',
    'eccv/2022/bevformer.html': 'https://github.com/fundamentalvision/BEVFormer',
    'eccv/2022/anydoor.html': 'https://github.com/ali-vilab/AnyDoor',
    'eccv/2022/petr.html': 'https://github.com/megvii-research/PETR',
    'eccv/2022/maskgit.html': 'https://github.com/google-research/maskgit',
    'eccv/2022/maxvit.html': 'https://github.com/google-research/maxvit',
    'eccv/2022/2dpass.html': 'https://github.com/yanx27/2DPASS',
    'eccv/2022/pose-ndf.html': 'https://github.com/garvita-tiwari/PoseNDF',
    'eccv/2022/partial-distance-correlation.html': 'https://github.com/zhenxingjian/Partial_Distance_Correlation',
    'eccv/2024/grounding-dino.html': 'https://github.com/IDEA-Research/GroundingDINO',
    'eccv/2024/sapiens.html': 'https://github.com/facebookresearch/sapiens',
    'eccv/2024/lgm.html': 'https://github.com/3DTopia/LGM',
    'eccv/2024/videomamba.html': 'https://github.com/OpenGVLab/VideoMamba',
    'eccv/2024/concept-sliders.html': 'https://github.com/rohitgandikota/sliders',
    'eccv/2024/sea-raft.html': 'https://github.com/princeton-vl/SEA-RAFT',
    'eccv/2024/adversarial-diffusion-distillation.html': 'https://github.com/Stability-AI/generative-models',
    'eccv/2024/sit.html': None,  # 移除誤判
    'eccv/2024/freeform-pixels.html': None,  # 不確定

    # ── ICCV ──
    'iccv/2013/overfeat.html': 'https://github.com/sermanet/OverFeat',
    'iccv/2015/c3d.html': 'https://github.com/facebookarchive/C3D',
    'iccv/2015/hed.html': 'https://github.com/s9xie/hed',
    'iccv/2015/flownet.html': 'https://github.com/lmb-freiburg/flownet2',
    'iccv/2015/fastrcnn.html': 'https://github.com/rbgirshick/fast-rcnn',
    'iccv/2015/prelu.html': None,  # 移除誤判（Emacs Prelude）
    'iccv/2015/crfrnn.html': 'https://github.com/sadeepj/crfasrnn_keras',
    'iccv/2017/cyclegan.html': 'https://github.com/junyanz/CycleGAN',
    'iccv/2017/maskrcnn.html': 'https://github.com/facebookresearch/Detectron',
    'iccv/2017/contextinpaint.html': 'https://github.com/JiahuiYu/generative_inpainting',
    'iccv/2017/channelpruning.html': 'https://github.com/yihui-he/channel-pruning',
    'iccv/2017/retinanet.html': 'https://github.com/facebookresearch/Detectron',
    'iccv/2017/gradcam.html': 'https://github.com/ramprs/grad-cam',
    'iccv/2017/segevery.html': 'https://github.com/ronghanghu/seg_every_thing',
    'iccv/2019/slowfast.html': 'https://github.com/facebookresearch/SlowFast',
    'iccv/2019/singan.html': 'https://github.com/tamarott/SinGAN',
    'iccv/2019/fcos.html': 'https://github.com/tianzhi0549/FCOS',
    'iccv/2019/votenet.html': 'https://github.com/facebookresearch/votenet',
    'iccv/2019/meshrcnn.html': 'https://github.com/facebookresearch/meshrcnn',
    'iccv/2019/cutmix.html': 'https://github.com/clovaai/CutMix-PyTorch',
    'iccv/2021/swin.html': 'https://github.com/microsoft/Swin-Transformer',
    'iccv/2021/maskformer.html': 'https://github.com/facebookresearch/MaskFormer',
    'iccv/2021/co3d.html': 'https://github.com/facebookresearch/co3d',
    'iccv/2021/pvt.html': 'https://github.com/whai362/PVT',
    'iccv/2021/mvit.html': 'https://github.com/facebookresearch/mvit',
    'iccv/2021/mipnerf.html': 'https://github.com/google/mipnerf',
    'iccv/2021/opengan.html': 'https://github.com/aimerykong/OpenGAN',
    'iccv/2023/sam.html': 'https://github.com/facebookresearch/segment-anything',
    'iccv/2023/controlnet.html': 'https://github.com/lllyasviel/ControlNet',
    'iccv/2023/anydoor.html': 'https://github.com/ali-vilab/AnyDoor',
    'iccv/2023/gaussiansplatting.html': 'https://github.com/graphdeco-inria/gaussian-splatting',
    'iccv/2023/omnimotion.html': 'https://github.com/qianqianwang68/omnimotion',
    'iccv/2023/lavie.html': 'https://github.com/Vchitect/LaVie',
    'iccv/2023/hqtrack.html': 'https://github.com/jiawen-zhu/HQTrack',
    'iccv/2023/lerf.html': 'https://github.com/kerrj/lerf',
    'iccv/2025/sa2va.html': 'https://github.com/bytedance/Sa2VA',
    'iccv/2025/longsplat.html': 'https://github.com/NVlabs/LongSplat',
    'iccv/2025/brickgpt.html': 'https://github.com/AvaLovelace1/BrickGPT',
    'iccv/2025/flowedit.html': 'https://github.com/fallenshock/FlowEdit',
    'iccv/2025/rayzer.html': 'https://github.com/hwjiang1510/RayZer',
    'iccv/2025/scenesplat.html': 'https://github.com/unique1i/SceneSplat',
    'iccv/2025/maskcontrol.html': 'https://github.com/exitudio/MaskControl',
    'iccv/2025/hermes.html': None,  # 移除誤判（Facebook JS 引擎）
}

# 移除明確誤判（自動查詢找到但完全不相關的）
FALSE_POSITIVES = {
    'cvpr/2013/facealign.html',     # roblourens/facealign — VS Code 套件
    'cvpr/2013/otb.html',           # orfeotoolbox/OTB — 衛星影像工具
    'cvpr/2013/multitarget.html',   # Smorodov/Multitarget-tracker — 不同的追蹤器
    'cvpr/2013/saliency.html',      # PAIR-code/saliency — Google 可解釋 AI 工具
    'cvpr/2013/pedestrian.html',    # 一般行人偵測 repo
    'cvpr/2014/mcg.html',           # mbitson/mcg — 不相關
    'cvpr/2014/liegroup.html',      # utiasSTARS/liegroups — 不同的 Lie 群庫
    'cvpr/2015/picture.html',       # LuckSiege/PictureSelector — Android 圖片選擇器
    'cvpr/2015/hypercolumns.html',  # 不相關
    'cvpr/2016/cycleconsist.html',  # 不同的 cycle consistency
    'cvpr/2019/librarcnn.html',     # 學生專案
    'cvpr/2022/minimalproblems.html', # 不確定是否正確
    'eccv/2014/microsoft-coco.html',  # 不是 COCO 官方
    'eccv/2014/scene-chronology.html', # NeuSC 是不同論文
    'eccv/2014/sds.html',           # antirez/sds — Redis 資料結構
    'eccv/2020/kdss.html',          # 不相關
    'eccv/2020/ocrnet.html',        # 學生專案
    'iccv/2013/absorbing.html',     # 馬可夫鏈數學 repo
    'iccv/2013/multilife.html',     # 遊戲 repo
    'iccv/2013/sceneflow.html',     # 不相關公司
    'iccv/2013/rgbd3d.html',        # LabVIEW 專案
    'iccv/2013/photoocr.html',      # 學生專案
    'iccv/2015/contextpred.html',   # 學生複製
    'iccv/2015/videorep.html',      # 不同論文
    'iccv/2017/firstperson.html',   # Godot 遊戲範本
    'iccv/2017/globalcomplete.html', # 學生專案
}


def embed_github_link(html_text, github_url):
    """在 navbar 中 arXiv 連結後面加入 GitHub 連結"""
    if not github_url:
        return html_text

    # 已有 GitHub 連結則跳過
    if 'github.com' in html_text[:3000] and 'GitHub' in html_text[:3000]:
        return html_text

    github_tag = (
        f'<a href="{github_url}" target="_blank" '
        f'class="navbar-home-link" style="margin-left:16px;">GitHub</a>'
    )

    # 找 arXiv 連結位置，在其後插入
    arxiv_pattern = r'(<a[^>]*href="https?://arxiv\.org/abs/[^"]*"[^>]*>[^<]*</a>)'
    m = re.search(arxiv_pattern, html_text[:3000])
    if m:
        insert_pos = m.end()
        return html_text[:insert_pos] + '\n            ' + github_tag + html_text[insert_pos:]

    # 找其他外部連結（CVF 等），在其後插入
    cvf_pattern = r'(<a[^>]*href="https?://[^"]*(?:thecvf|cv-foundation)[^"]*"[^>]*>[^<]*</a>)'
    m = re.search(cvf_pattern, html_text[:3000])
    if m:
        insert_pos = m.end()
        return html_text[:insert_pos] + '\n            ' + github_tag + html_text[insert_pos:]

    # 找返回主頁連結，在其後插入
    home_pattern = r'(<a[^>]*class="navbar-home-link"[^>]*>[^<]*返回主頁[^<]*</a>)'
    m = re.search(home_pattern, html_text[:3000])
    if m:
        insert_pos = m.end()
        return html_text[:insert_pos] + '\n            ' + github_tag + html_text[insert_pos:]

    return html_text


def main():
    dry_run = '--dry-run' in sys.argv

    # 載入自動查詢結果
    if INPUT_JSON.exists():
        data = json.loads(INPUT_JSON.read_text(encoding='utf-8'))
    else:
        data = {}

    print(f'載入自動查詢結果：{len(data)} 篇')

    # 套用修正
    curated = {}
    added = 0
    removed = 0
    corrected = 0

    for path, info in data.items():
        entry = dict(info)

        # 套用已知正確 repo
        if path in KNOWN_REPOS:
            new_url = KNOWN_REPOS[path]
            old_url = entry.get('github_url')
            if new_url != old_url:
                if new_url:
                    entry['github_url'] = new_url
                    entry['curated'] = True
                    if old_url:
                        corrected += 1
                    else:
                        added += 1
                else:
                    entry['github_url'] = None
                    entry['stars'] = 0
                    entry['curated'] = True
                    if old_url:
                        removed += 1

        # 移除已知誤判
        elif path in FALSE_POSITIVES:
            if entry.get('github_url'):
                entry['github_url'] = None
                entry['stars'] = 0
                entry['curated'] = True
                removed += 1

        curated[path] = entry

    # 加入 KNOWN_REPOS 中有但 data 中沒有的
    for path, url in KNOWN_REPOS.items():
        if path not in curated and url:
            curated[path] = {
                'title': None,
                'github_url': url,
                'stars': 0,
                'curated': True,
            }
            added += 1

    # 統計
    with_repo = {k: v for k, v in curated.items() if v.get('github_url')}
    print(f'修正後：{len(with_repo)} 篇有 GitHub 連結')
    print(f'  新增：{added}，修正：{corrected}，移除誤判：{removed}')

    # 儲存修正後結果
    OUTPUT_JSON.write_text(
        json.dumps(curated, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f'已儲存至：{OUTPUT_JSON}')

    if dry_run:
        print('\n[DRY RUN] 不寫入 HTML')
        return

    # 嵌入 GitHub 連結至 HTML
    print(f'\n嵌入 GitHub 連結至 HTML...')
    embedded = 0
    skipped = 0
    errors = 0

    for path, info in sorted(with_repo.items()):
        github_url = info['github_url']
        html_path = BASE / path

        if not html_path.exists():
            continue

        try:
            html = html_path.read_text(encoding='utf-8')

            # 已有 GitHub 連結 → 跳過
            if 'GitHub</a>' in html[:3000]:
                skipped += 1
                continue

            new_html = embed_github_link(html, github_url)
            if new_html != html:
                html_path.write_text(new_html, encoding='utf-8')
                embedded += 1
                print(f'  [OK] {path}')
            else:
                skipped += 1
        except Exception as e:
            print(f'  [ERR] {path}: {e}')
            errors += 1

    print(f'\n完成：嵌入 {embedded} 篇，跳過 {skipped} 篇，錯誤 {errors} 篇')


if __name__ == '__main__':
    main()
