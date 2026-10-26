# 女装 Lookbook Skill (gpt-womens-lookbook)

基于公开女装摄影教程重建的 Lookbook 动作与提示词工作流。通过“衣服先行”原则，根据模特的服装版型、结构与风格情绪，从随包动作库中匹配动作、眼神与表情，支持只生成提示词或串行生成多姿势系列图。

> **公开发布说明**：本项目已经用户授权公开发布。包内包含完整动作原页、视频证据帧、动作区域索引、提示词模板及离线查询校验工具。

## 核心设计与执行规范

- **主入口**：[SKILL.md](SKILL.md) 为技能核心规约。
- **四种参考职责**：在开始执行前，分清模特身份、服装商品、场景空间与本张动作参考四个控制维度；一组固定人物、服装与场景，每张独立选姿，一组照片中保持模特面孔与商品细节严格一致。
- **衣服先行**：看服装的版型、长度、剪裁与面料垂坠感，先选定需要展示的服装细节，再匹配合适的人物动作幅度、重心支撑、视线与表情，拒绝生硬摆拍。
- **N 次串行单图**：总张数 N 拆解为 N 次单图任务独立执行。每张均回到初始固定的模特、服装与场景基准，上一张的生成结果不作为下一张的基准，避免误差累积。
- **仅写词不生成模式**：支持仅输出语义精准、参数已替换的中英文提示词而不调用图像生成，降低试错成本。

## 资产与目录构成

本包完整保留以下 34 个核心文件及资产（逐字节无损收录）：

1. **动作原页（19 页）**：位于 `assets/pose-pages/`
   - `01.webp` ～ `18.webp`：18 张动作参考大页（共收录标注 155 个动作区域）。
   - `19.webp`：规则与安装说明页。
2. **视频证据帧（4 帧）**：位于 `assets/tutorial-frames/`
   - 收录 `source-025s.jpg`、`source-065s.jpg`、`source-085s.jpg`、`source-110s.jpg`，存证视频中工作流界面、参数配置及版本声明。
3. **动作索引**：[references/image-pose-index.json](references/image-pose-index.json) 包含 155 个姿势的归一化裁切框坐标 `[x, y, w, h]`、景别、姿态描述与中文标签。
4. **工作流与参考文档**：
   - [SKILL.md](SKILL.md)：主规约
   - [references/workflow.md](references/workflow.md)：详细判定逻辑与失败修正
   - [references/prompts.md](references/prompts.md)：可直接复制的中英文双语提示词模板
   - [references/pose-library.md](references/pose-library.md)：动作库坐标与裁剪规范
   - [references/sources.md](references/sources.md)：来源存证与版本比对
   - [references/asset-manifest.json](references/asset-manifest.json)：素材哈希清单
   - [agents/openai.yaml](agents/openai.yaml)：OpenAI 界面定义
5. **脚本工具**：
   - `scripts/check_package.py`：包完整性只读自检工具（零第三方依赖）。
   - `scripts/query_poses.py`：离线动作索引查询与裁剪工具（查询仅依赖 Python 标准库）。

## 使用示例

### Agent 调用

在支持 Skill 的智能体环境中输入：
```text
使用 $gpt-womens-lookbook，根据我的模特、服装和场景制作一组女装 Lookbook。
```

### 离线动作检索

无需联网，使用 Python 标准库即可快速检索动作：

```bash
# 查询指定编号动作（例如 001 号）
python3 scripts/query_poses.py --figure-id 001 --json

# 按景别与动作类型筛选
python3 scripts/query_poses.py --framing full --action standing --limit 6

# 关键词中文搜索
python3 scripts/query_poses.py --search 回望 --json
```

脚本需要 Python 3.9+。若需根据坐标裁剪单张动作，环境另需 Pillow，且输出目录须存在：
```bash
mkdir -p output
python3 scripts/query_poses.py --id p01-f001 --crop-output output/crop_001.png
```

### 完整性自检

运行只读完整性校验：
```bash
python3 scripts/check_package.py --json
```

## 版本差异与出处边界

- **版本规模差异**：
  原作者视频演示（EP47）中提及“25页 / 187参考”；而公开配套图文实际发布为“18动作页＋1规则页 / 155示例”。本项目实事求是严格以实际取得的 19 张原图及 155 个有效区域建档，不凭空捏造本次未取得的差额素材。详细差异分析见 [references/sources.md](references/sources.md)。
- **版权与许可边界**：
  - 本项目的提炼结构采用女娲技能框架（MIT License，作者：花叔），许可声明保留于 [LICENSE.nuwa](LICENSE.nuwa)。
  - 原视频与图文教程作者为 **普渡众神花**（UID: 66519190620）。本包保留原作者出处与素材归属，不擅自将第三方原创音画素材重新定义为统一媒体 MIT 授权。
- **效果边界**：
  本包完成的本地文件结构、索引坐标与提示词逻辑校验，**不代表**真实生图效果（如特定商品细节还原、头身比真实感、表情贴合度）已完成视觉验收；实际出图表现取决于下游图像生成模型的具体能力。
