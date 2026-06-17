# 从机器人中心到空间模型中心：通用手术导航的趋势综述

## 摘要

手术 AI 的下一阶段发展，可能不只是二维视频理解模型的性能提升，也不只是将更复杂的算法封装进更昂贵的机器人平台。本文基于价值医疗、手术数据科学、内窥镜三维重建和基础模型相关文献，提出一种更谨慎的趋势判断：通用手术导航的核心竞争正在从机器人硬件中心，逐步转向可跨硬件部署的手术空间模型中心。该判断并不否认高端机器人在复杂术式和高资源中心的价值，而是指出，如果目标是构建可普及、可泛化、可持续更新的通用导航能力，算法能力不宜完全绑定于资本密集型、装机量有限、数据生态封闭的专有平台。机器人与腹腔镜手术的随机试验证据和经济学综述提示，新技术采用需要跨越临床价值与系统成本的双重门槛 [CITE: Kawka2023; Marcus2024; Sadri2023; Lai2024; Bosscha2026]。

数据层面，当前 surgical scene understanding 研究已显示小规模单中心数据、腹腔镜胆囊切除术集中、外部验证不足和临床转化有限等问题 [CITE: Carstens2026]。这说明手术 AI 的主要瓶颈并非单个模型是否足够复杂，而是能否形成覆盖多医院、多设备、多术式、多术者和长尾风险状态的真实世界数据飞轮。技术层面，NeRF、3D Gaussian Splatting、SLAM、SDF、点云、mesh 和 surgical foundation models 均提供了重要组件，但它们大多仍集中于可见表面、深度、pose 或视频表征，尚不足以单独构成临床级通用导航系统 [CITE: EndoNeRF2022; Deform3DGS2024; EndoDAC2024; Endo3R2025]。本文因此提出一种路线假设：以粗糙三维先验和连续 RGB 视频为输入，在模型内部维护可持续更新的 latent spatial memory，并按任务解码为可渲染场景、显式几何、拓扑结构、相机位姿、不确定性和风险区域。落地上，腹腔镜胆囊切除术更适合作为视频语义安全辅助和数据飞轮入口，而肝、肾、胰、前列腺等强术前影像依赖术式更适合作为术前-术中三维配准导航的验证场 [CITE: Mascagni2024; Cholec80CVS2023; Endoscapes2025; Dai2025]。本文不声称该路线已经成熟；相反，文章最后列出模型、数据、临床价值和成本证据缺口，并将若干图表数据标记为 USER_GATE。

## 1. 引言：为什么手术 AI 不能只按机器人硬件叙事理解

过去十余年，手术机器人和手术 AI 经常被放在同一个技术叙事中：更精密的器械、更稳定的操控、更高分辨率的视觉、更复杂的算法，似乎自然会导向更好的手术。然而，临床采用并不只由技术复杂度决定。对于医院、支付方和外科团队而言，一套新系统必须回答更朴素的问题：它是否减少了真实风险，是否改善了流程或结局，是否降低了总拥有成本，是否缩短学习曲线，是否能够在足够多的真实场景中稳定工作 [CITE: Marcus2024; Lai2024]。

这并不是否认机器人平台的价值。高端机器人在部分复杂盆腔、泌尿、胸外和精细重建场景中可能提供稳定视野、灵活器械、人体工程学和训练价值。问题在于，若将通用手术导航的未来完全理解为“更昂贵、更封闭、更全能的机器人平台”，就会忽略两条更底层的约束。第一是卫生经济学约束：先进设备不必然等于可普及设备；第二是数据约束：通用 AI 需要覆盖真实世界长尾分布，而不是只学习高资源中心、少数术式和特定设备生态中的局部数据 [CITE: Kawka2023; Carstens2026]。

本文的核心判断是：下一代通用手术导航更可能是一种空间模型基础设施，而不只是某个机器人硬件平台。标准内窥镜和腹腔镜系统已经存在于广泛手术室中，可作为低摩擦数据采集与部署终端；粗糙三维先验、术中 RGB 视频、几何推理和 latent spatial memory 则可能成为软件层面的能力中心。由此，机器人可以是重要终端之一，但不必是算法能力和数据飞轮的唯一载体 [CITE: Protserov2024; Mascagni2024]。

## 2. 卫生经济学约束：先进不等于可普及

手术 AI 的价值不应只用 Dice、mAP、AUC、PSNR 或 pose error 表达。对于临床系统而言，这些指标只有在改变手术过程、患者风险、资源消耗或学习曲线时，才会成为可采纳的价值。机器人与腹腔镜腹部/盆腔手术的随机试验证据表明，机器人平台并未在所有术式和结局上稳定优于腹腔镜，并且成本、手术时间和组织影响经常成为评价重点 [CITE: Kawka2023; Bosscha2026]。经济学综述也提示，机器人手术是否具有成本效果，依赖病例量、平台共享、长期结局、住院时间、学习曲线和定价等条件，而不是由“机器人化”本身保证 [CITE: Sadri2023; Lai2024]。

这对手术 AI 导航提出了一个价值框架：系统若要大规模扩散，至少需要满足两类路径之一。第一类是“增益其所不能”，即提供传统二维屏幕、裸眼经验或手工操作难以提供的能力，例如深部解剖结构感知、风险边界提示、三维位姿维持和不确定性可视化。第二类是“高性价比普适化”，即以较低边际成本扩大优质手术能力覆盖范围，例如在非顶级中心提升流程标准化、训练效率和风险识别能力。真正值得关注的路线，应当尽量同时回应二者：既降低数据和部署成本，又提供超越普通二维视野的空间理解能力。

**Figure 1 Placeholder: Clinical Value-Cost Landscape of Surgical AI and Navigation Systems**

Draft SVG: `auto_paper_output/surgical-ai-review/figures/fig_001_value_cost_landscape.svg`

> Caption draft: 该图是价值评估框架，而非现有系统的确定性排名。横轴表示增量成本或每例总拥有成本，纵轴表示增量临床价值。传统腹腔镜、高端机器人、当前二维手术 AI 和硬件无关 AI 导航应以不确定性区域表示；其中硬件无关 AI 导航仅作为本文提出的 hypothesized target zone，尚需临床价值和成本效果证据验证 [CITE: Kawka2023; Marcus2024; Sadri2023; Lai2024; Bosscha2026]。USER_GATE: 若要做实证坐标图，需要成本、结局和系统集成费用数据。

## 3. 数据瓶颈：从手术数据飞轮到分布坍缩

通用手术 AI 的核心资产不是一次性训练好的模型，而是持续运行的数据飞轮：手术视频采集、弱监督或专家标注、模型预训练、临床静默部署、术者反馈、术中事件、术后结局链接、再训练和真实世界监测。没有这个闭环，模型很容易停留在离线 benchmark 中的高分，而无法覆盖手术室中的设备差异、照明变化、术者风格、炎症粘连、解剖变异和罕见并发症。

当前文献已经显示出数据基础的狭窄性。最新 surgical scene understanding 系统综述纳入 188 项研究，并指出小规模单中心数据、LC 术式集中、外部验证不足和临床转化有限是关键问题 [CITE: Carstens2026]。这些证据足以支持“数据分布坍缩”的谨慎表述：领域并非没有数据，而是可公开、可标注、可复用、可外部验证、可链接结局的数据分布过窄。

高端机器人数据并非没有价值。相反，机器人平台可以提供稳定视野、器械运动、双目视频和控制信号，对技能评估、动作学习和机器人控制非常重要。但若通用手术 AI 的数据底座只来自封闭、高成本、装机量有限的平台，则数据会天然偏向高资源中心、特定术式、特定术者群体和特定设备代际。机器人数据采集本身也需要专门链路、事件解析和标注流程 [CITE: Hashemi2023]。此外，AI 技能评估研究中的偏差问题提醒我们，手术 AI 的泛化与公平性不能只靠“更多视频”自然解决 [CITE: Kiyasseh2023]。

标准内窥镜/腹腔镜的优势在于覆盖面。它不是因为更“智能”而重要，而是因为它已经嵌入更多医院、术式和患者场景，更适合作为低摩擦视频入口。OR-ready、equipment-agnostic AI 的早期研究显示，手术视频流可以成为实时 AI 系统的部署入口 [CITE: Protserov2024]。LC 相关公开数据集，例如 Cholec80-CVS 和 Endoscapes，也说明高频标准化术式可以成为语义安全辅助和 CVS 评估的早期数据基础 [CITE: Cholec80CVS2023; Endoscapes2025]。

**Figure 2 Placeholder: Dataset Concentration and Long-Tail Bias in Surgical AI**

Draft SVG: `auto_paper_output/surgical-ai-review/figures/fig_002_dataset_concentration.svg`

> Caption draft: 四联图规划。Panel A: 公开手术视频数据集地理来源地图；Panel B: 术式或任务长尾分布，至少用 SSU 系统综述中 LC 集中和外部验证不足的统计作背景；Panel C: 机构数量 vs 视频数量气泡图；Panel D: 数据多样性雷达图，维度包括地理多样性、术式多样性、设备多样性、标注密度、结局链接和外部验证 [CITE: Carstens2026; Cholec80CVS2023; Endoscapes2025]。USER_GATE: Panel A/C/D 需要 dataset metadata CSV，不能凭 PDF 印象直接绘制。

## 4. 技术范式：从二维视频理解到可持续更新的三维空间状态

二维场景理解能解决许多重要任务：阶段识别、器械检测、解剖结构分割、CVS 判断、流程质量控制等。它们对 LC 等高频术式的安全辅助很有价值。但真正的手术导航不只问“当前画面中有什么”，还问“当前镜头在患者三维空间中的什么位置”“被遮挡或深部的关键结构可能在哪里”“牵拉、气腹、通气和切割之后，术前地图与术中真实解剖相差多少”“系统对这些估计有多不确定”。

这使手术场景不同于普通视频理解，也不同于许多刚体环境中的 3D 感知。医学场景拥有术前 CT、MRI、超声、器官 atlas 或手术规划模型等粗糙三维先验；但这些先验在术中会被非刚性形变、部分可见性、器械遮挡、烟雾、血液、冲洗液和拓扑变化不断破坏。肝脏运动和变形研究说明，通气、气腹和手术状态会造成术前模型与术中解剖之间的动态失配 [CITE: Sommer2024]。腹腔镜肝脏术前-术中表面配准研究也显示，术前 CT 提取模型与术中表面重建之间的配准受到非刚性变形、部分可见和重建噪声限制 [CITE: Dai2025]。

因此，手术导航需要的不是单次漂亮重建，而是可持续更新的空间状态。这个状态至少应包含当前相机 pose、已观察区域几何、粗糙先验中的未观察结构、当前帧与全局空间的对应关系、动态区域更新、不确定性和可供导航使用的拓扑或结构关系。NeRF、3DGS、SDF、点云和 mesh 都可以是输出表示或中间组件，但不应被写成完整答案。EndoNeRF 和 Deform3DGS 等工作展示了动态可见表面重建和快速渲染的潜力 [CITE: EndoNeRF2022; Deform3DGS2024]；EndoDAC、Endo3R 等工作把深度、pose 或在线重建能力推向手术场景 [CITE: EndoDAC2024; Endo3R2025]。但这些能力仍不同于临床导航所需的长期空间记忆、深部结构绑定、拓扑变化处理和失败检测。

## 5. 空间模型路线：粗糙 3D 先验 + RGB 视频 + latent spatial memory

本文更倾向于把未来的通用导航模型理解为 prior-guided latent spatial memory model，而不是某一种固定三维表示。其输入不应只有 RGB，也不应只有术前 CT，而应包含：

1. 粗糙三维先验：术前 CT/MRI/超声重建、器官 atlas、腔道模板、粗糙 mesh/point cloud 或手术规划模型；
2. 连续 RGB 或双目内窥镜视频；
3. 当前或估计相机运动；
4. 可选辅助信号，例如 ICG、术中超声、器械轨迹、深度或质量控制信号。

模型内部维护一个 latent memory bank，其中的 spatial tokens 不必一开始就是 point cloud 或 mesh。它们更像带空间索引的状态变量：既保留粗糙先验提供的尺度、拓扑和结构假设，也根据术中视频不断修正局部几何、对应关系和不确定性。通用 3D foundation models 提供了启发：DUSt3R 将多视图几何任务统一到 pointmap 预测框架，VGGT 直接预测相机参数、point maps、depth maps 和 3D tracks，CUT3R 强调 persistent state 的连续 3D 感知 [CITE: DUSt3R2024; VGGT2025; CUT3R2025]。但这些是通用视觉方向，不能直接当成手术导航证据。手术场景仍需要适配组织形变、受限视角、遮挡、镜头污染和临床安全边界。

在这个框架中，NeRF、3DGS、SDF、point cloud、mesh、pose 和 topology graph 都可以是 decoder 输出。3DGS 适合可视化和快速渲染，mesh 适合测量与拓扑，point cloud 适合局部几何，SDF/occupancy 适合连续表面或体积表示，pose 是导航必要输出，不确定性则是安全接口。视频基础模型如 Endo-FM、SurgVISTA 和 EndoMamba 说明内窥镜视频表征正在从任务专用模型走向大规模时空预训练 [CITE: EndoFM2023; SurgVISTA2026; EndoMamba2025]。但本文的关键区分是：video foundation model 学习“如何理解视频”，而 surgical spatial world model 还要学习“如何维护可导航的空间状态”。

**Figure 3 Placeholder: Layer-wise Research Landscape for Surgical Spatial World Models**

Draft SVG: `auto_paper_output/surgical-ai-review/figures/fig_003_layered_spatial_world_models.svg`

> Caption draft: 图 3 不是单一系统架构宣称，而是研究景观图。六层依次为：Coarse 3D Prior Layer、RGB Observation Layer、Geometry Inference Layer、Latent Spatial Memory Layer、Multi-Representation Decoder Layer、Navigation Interface Layer。每层右侧列出 Representative Methods、What It Solves、Why It Is Not Enough。EndoNeRF、Deform3DGS、EndoDAC、Endo3R、Endo-FM、SurgVISTA、DUSt3R、VGGT、CUT3R 等应被放在对应层级，强调组件级贡献和未解决问题 [CITE: EndoNeRF2022; Deform3DGS2024; EndoDAC2024; Endo3R2025; EndoFM2023; SurgVISTA2026; DUSt3R2024; VGGT2025; CUT3R2025]。

## 6. 落地路线：LC 视频安全辅助是入口，强术前影像术式是三维导航验证场

落地路线需要避免两个极端。一个极端是直接追求全术式、全自动、完整三维导航；另一个极端是停留在二维视频识别，把阶段识别、器械检测或语义分割等同于导航。更务实的路线应分为并行演进的三条轨道：数据与部署终端、模型能力、临床任务。

LC 适合作为第一阶段入口，因为它高频、流程相对标准化、公开视频和 CVS 标注基础较好，且安全目标明确。Cholec80-CVS 和 Endoscapes 为 LC 中的 CVS 判断、肝胆三角结构理解和语义安全辅助提供了数据基础 [CITE: Cholec80CVS2023; Endoscapes2025]。SurgFlow 等早期真实手术室部署研究也说明，LC 中的阶段识别、器械追踪、解剖分割和 CVS 评估可以作为实时 AI 辅助的可行性验证 [CITE: Mascagni2024]。但这类证据不应被写成“已降低胆管损伤”或“已改善患者结局”。它更适合支持“LC 是数据飞轮和安全语义辅助入口”的说法。

真正检验三维导航价值的场景，可能是肝、肾、胰、前列腺和复杂盆腔等强术前影像依赖术式。在这些场景中，术前 CT/MRI/超声对血管、肿瘤边界、胆管、神经或切除平面的信息更直接；术中则需要表面重建、刚性初始化、非刚性配准、生物力学或解剖先验、不确定性显示和 AR/风险地图输出 [CITE: Dai2025; Sommer2024]。因此，LC 与强影像术式不应被排成“LC 成功后自然推广到全术式”的单线进化，而应被视为两类互补验证场：前者验证低摩擦视频数据和语义安全辅助，后者验证粗糙先验到术中空间状态的三维导航闭环。

**Figure 4 Placeholder: Three-Lane Roadmap toward Hardware-Agnostic Surgical Spatial Intelligence**

Draft SVG: `auto_paper_output/surgical-ai-review/figures/fig_004_three_lane_roadmap.svg`

> Caption draft: 三轨路线图。轨道 A 是数据与部署终端：单中心公开视频数据集、多中心视频采集、静默部署、术者反馈与结局链接、跨设备数据飞轮。轨道 B 是模型能力：二维场景理解、深度/pose/pointmap、粗糙先验引导 3D refine、latent spatial memory、多表示解码、可查询空间世界模型。轨道 C 是临床任务：LC 阶段识别/器械识别/CVS、Go/No-Go 安全提示、强影像术式术前-术中配准、AR 导航与风险地图、跨术式辅助。颜色深浅表示证据强度；浅色虚线表示趋势假设 [CITE: Protserov2024; Mascagni2024; Cholec80CVS2023; Endoscapes2025; Dai2025; Endo3R2025]。

## Table 1. Evidence Ledger

| value constraint or claim | representative support | support grade | what it supports | remaining limitation |
| --- | --- | --- | --- | --- |
| 技术先进不自动等于可普及 | Kawka2023; Marcus2024; Sadri2023; Lai2024; Bosscha2026 | strong plus partial plus limiting | 采用评价需要临床价值、成本、学习曲线、系统影响和长期监测 | 不能推导为高端机器人无价值 |
| SSU 数据存在集中和验证缺口 | Carstens2026 | strong | 单中心、小规模、术式集中、外部验证不足、临床转化不足 | 具体百分比提交前需全文核验 |
| 机器人数据有价值但采集有工程摩擦 | Hashemi2023 | partial | da Vinci Si/Xi 数据采集、事件解析、标注流程需要专门链路 | 不等于所有机器人平台都不可扩展 |
| 标准视频流可作为设备无关 AI 入口 | Protserov2024 | partial | OR-ready、equipment-agnostic real-time AI 的系统可行性 | 不等于患者结局或成本效果已证明 |
| LC 是语义安全辅助入口 | Mascagni2024; Cholec80CVS2023; Endoscapes2025 | strong for data/feasibility | LC/CVS 数据和早期实时辅助可行性 | 不等于完整三维导航终点 |
| 术前-术中三维导航需要处理形变和配准 | Sommer2024; Dai2025 | partial | 肝脏运动、气腹/通气影响、术前 CT 与术中表面配准挑战 | 仍需跨患者、跨设备、临床级验证 |
| NeRF/3DGS 是重要组件而非完整答案 | EndoNeRF2022; Deform3DGS2024 | partial plus limiting | 可见表面重建、渲染、快速 reconstruction | 不解决深部结构、拓扑变化、临床导航闭环 |
| 空间模型路线需要 latent memory 和多表示解码 | Endo3R2025; DUSt3R2024; VGGT2025; CUT3R2025 | partial plus background | 几何推理、pointmap、pose、persistent state 的技术启发 | General 3D models 不是手术验证证据 |
| Figure 2 实证面板需要数据集元信息 | EndoVis; CAMMA_datasets; Endoscapes2025; Cholec80CVS2023 | metadata_only plus examples | 可作为数据表构建入口 | USER_GATE: 未完成 dataset metadata CSV |

## 7. 当前证据缺口和风险

第一，模型证据缺口仍然很大。现有 EndoNeRF、Deform3DGS、EndoDAC、Endo3R 等方向说明术中可见表面重建、深度估计、pose 和在线几何正在进步 [CITE: EndoNeRF2022; Deform3DGS2024; EndoDAC2024; Endo3R2025]。但导航所需的长期空间一致性、动态软组织地图维护、切割后的拓扑变化、血液/烟雾/冲洗液遮挡、尺度漂移和失败检测仍缺少充分证据。尤其是深部胆管、血管、神经、肿瘤边界等不可见结构，不能由表面重建直接安全推出。

第二，数据证据缺口不能忽略。SSU 系统综述支持单中心、术式集中和外部验证不足等判断 [CITE: Carstens2026]，但若要画出地理来源地图、头部中心偏置、机构数量 vs 视频数量气泡图或数据多样性雷达图，需要逐项编码公开数据集元信息。本文将 Figure 2 的 Panel A/C/D 标为 USER_GATE，而不是把 PDF 中的图表设想直接画成实证结论。

第三，临床价值证据仍处于早期。SurgFlow 等工作支持真实手术室中的实时 AI feasibility [CITE: Mascagni2024]，但 feasibility 不等于 patient outcome improvement。未来评价不应只包括 Dice、mAP、PSNR、ATE 或 pose error，还应包括外科医生是否更快定位关键结构、是否减少错误解剖、是否降低转开腹率、是否缩短学习曲线、是否减少并发症、是否在可接受成本下部署，以及 AI 提示被采纳或忽略后的责任与审计链路。

第四，成本证据可能反向约束硬件无关路线。若所谓“标准内窥镜 AI 导航”仍需要昂贵 GPU、复杂视频接口、专用网络、手术室级 IT 集成和高维护成本，它就可能重新形成资本密集型壁垒。因此，Figure 1 中的“低成本高价值目标区”必须保持虚线表示，直到边缘算力、部署维护、培训、网络安全和总拥有成本被量化。

## 结论

本文提出的不是一个已被临床证明的终局，而是一种关于通用手术导航的趋势综述：未来的关键可能不在于选择 NeRF、3DGS、SDF、点云或 mesh 中的某一种表示，也不在于让所有智能能力绑定到单一高端机器人平台，而在于构建能够融合粗糙三维先验和连续 RGB 观测的 latent spatial memory。这个 memory 应该持续更新场景状态，并按任务解码为可渲染表示、显式几何、拓扑结构、当前相机 pose、不确定性和风险区域。

标准内窥镜/腹腔镜系统提供低摩擦数据与部署入口，LC 提供高频语义安全辅助和数据飞轮入口，强术前影像依赖术式提供真正三维配准导航的验证场，视频基础模型和 3D foundation models 提供空间世界模型的技术启发。但这些线索尚未汇合成成熟临床导航系统。最严谨的表述应是：从机器人中心到空间模型中心，是一种值得关注的路线假设；它的价值取决于后续能否补齐真实世界数据、长期空间一致性、拓扑变化处理、临床结局、总拥有成本和监管级安全边界等证据。

## Verified Reference Plan

已完成 metadata-level 核验并用于正文的引用占位包括：Kawka2023, Sadri2023, Marcus2024, Lai2024, Bosscha2026, Carstens2026, Kiyasseh2023, Hashemi2023, Protserov2024, Mascagni2024, Cholec80CVS2023, Endoscapes2025, Sommer2024, Dai2025, EndoNeRF2022, Deform3DGS2024, EndoFM2023, SurgVISTA2026, EndoDAC2024, Endo3R2025, DUSt3R2024, VGGT2025, CUT3R2025, EndoMamba2025。

仍需人工确认或全文核验后才能进入正式参考文献表的候选包括：Yang2025_BiomechanicalSurfaceMatching, EndoGSLAM, SurgicalGaussian, EndoGS/EndoGaussian, ROLARR, RAZOR, DECIDE-AI, FDA_PCCP, NMPA_pretraining_model_guidance，以及 Figure 2 所需的 EndoVis、JIGSAWS、M2CAI、HeiChole、CholecSeg8k、CaDIS、CATARACTS、SCARED、Hamlyn、SurgVU、SLAM20 等 dataset metadata。

## Gate Status

USER_GATE: 需要人工确认未核验引用、补 Figure 2 dataset metadata CSV，并在正式发布前全文核对关键百分比、成本数字和图表面板数据。

RUN_REQUEST: NOT_RUN. 当前缺口是文献核验和图表数据整理，不是本地实验、训练或评估需求。
