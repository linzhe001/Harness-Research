# Confirmed Motivation

本文的核心动机不是写一篇无引用观点文，而是把 PDF 中形成的趋势判断重写成 citation-supported 技术综述。

## Thesis

手术 AI 的下一阶段可能不只是二维视频模型性能提升，也不只是把更复杂算法封装进更昂贵的机器人平台，而是转向一种硬件无关的空间模型路线：以标准内窥镜/腹腔镜作为低摩擦数据与部署入口，以粗糙三维先验和术中 RGB 视频作为输入，在模型内部维护可持续更新的 latent spatial memory，并根据任务解码为几何、pose、拓扑、可渲染视图和风险提示。

## Boundary

该 thesis 是趋势判断，不是临床终局声明。正文必须持续使用以下边界：

- high-end robots: valuable in selected contexts, but not the only plausible data/AI substrate;
- LC: data flywheel and semantic safety-assistance entry, not final 3D navigation endpoint;
- NeRF/3DGS/SDF/SLAM: components and intermediate representations, not full navigation answers;
- patient outcomes: not broadly proven by the verified references in this pass;
- Figure 2 empirical panels: USER_GATE until dataset metadata is manually coded.
