# Motivation Surface Map

| section | reader_question | motivation_answer | claim_ids | citation_ids |
| --- | --- | --- | --- | --- |
| Abstract | 这篇文章的中心判断是什么？ | 从机器人硬件中心转向空间模型中心是一种值得关注但尚未完成的通用手术导航趋势。 | claim_001; claim_003; claim_004; claim_006 | cite_001; cite_002; cite_006; cite_009; cite_015; cite_016 |
| 引言 | 为什么不能只按机器人硬件叙事理解手术 AI？ | 临床采用取决于价值和经济约束；硬件先进性不是充分条件。 | claim_001 | cite_001; cite_002; cite_003; cite_004; cite_005 |
| 卫生经济学约束 | 为什么“先进”不等于“可普及”？ | 机器人/导航系统需要证明患者、流程或系统价值，并处理成本、学习曲线和组织影响。 | claim_001 | cite_001; cite_002; cite_003; cite_004; cite_005 |
| 数据瓶颈 | 为什么数据飞轮不宜只绑定封闭高端平台？ | 当前 SSU 文献已有单中心、术式集中和外部验证不足问题；机器人数据也需额外采集和标注链路。 | claim_002; claim_003 | cite_006; cite_007; cite_008; cite_009 |
| 技术范式 | 为什么二维视频理解不够？ | 导航需要 pose、geometry、topology、uncertainty 和与粗糙三维先验绑定的持续空间状态。 | claim_004; claim_006 | cite_013; cite_014; cite_015; cite_016; cite_019; cite_020 |
| 空间模型路线 | 为什么提出 rough prior + RGB + latent spatial memory？ | 它把 3D 表示从终点改为 decoder 输出，把核心放在可在线更新的状态。 | claim_004 | cite_017; cite_018; cite_020; cite_021; cite_022; cite_023 |
| 落地路线 | 为什么 LC 是入口、强影像术式是 3D 导航验证场？ | LC 有视频/CVS 数据和早期实时 AI 可行性；肝等术式更能检验术前影像到术中配准。 | claim_005 | cite_010; cite_011; cite_012; cite_014 |
| 证据缺口 | 为什么最终返回 USER_GATE？ | 引用和 Figure 2 实证图表数据尚未完成全量人工核验。 | claim_006; claim_007 | cite_006; cite_024; cite_025 |
