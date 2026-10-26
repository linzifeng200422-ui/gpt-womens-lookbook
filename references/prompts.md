# 中英文提示词模板

下面是依据教程规则编写的本地模板，不是作者后台完整提示词。使用时把括号变量替换为本次已核事实；不要把路径文字当作图像已经上传。两种语言的锁定项、动作、景别和尺寸应一致。

## 单张 Lookbook

中文：
> 生成一张女装 Lookbook 照片。模特参考〔M〕只控制人物身份、发型与可见身体比例；服装参考〔O〕控制〔具体服装结构、面料、颜色、搭配及关键细节〕；场景参考〔S〕控制〔背景、空间、光线与地面〕。动作参考〔复合ID及单人物裁片〕只控制动作、视线、表情与景别，不采用其人物身份、穿搭或背景。本张使用〔景别〕，〔具体承重、身体朝向、手部动作〕，视线〔方向〕，表情〔强度和状态〕。选择这个动作是为了〔展示商品与服装情绪的理由〕。保留〔必须可见的关键部位〕，保持动作可执行、头身比与手足结构自然。保持本张动作参考原有景别，不凭空补全其画外动作信息；不要把身份参考的单个角度误当作所有身体信息。不要生成拼版。画幅〔比例〕，目标〔宽×高〕像素，只输出一张。

English:
> Create one womenswear lookbook photograph. Model reference [M] controls identity, hair, and visible body proportions only. Outfit reference [O] controls [specific construction, fabric, color, styling, and key details]. Scene reference [S] controls [background, space, lighting, and floor]. Pose reference [composite ID and single-figure crop] controls movement, gaze, expression, and framing only; do not copy its identity, outfit, or background. Use [framing], with [specific weight shift, body orientation, and hand action], looking [direction], with [expression and intensity]. This pairing should [reason related to garment visibility and mood]. Keep [critical details] visible. Maintain physically plausible movement, natural head-to-body proportions, and coherent hands and feet. Preserve the pose reference’s framing without inventing its unseen action or limb configuration; do not confuse one view of the identity reference with complete body evidence. Do not create a collage. Aspect ratio [ratio], target dimensions [width × height] pixels, one image only.

## 定向修复

中文：
> 仍使用原来的模特〔M〕、服装〔O〕、场景〔S〕和动作〔ID〕。只修复〔已观察到的问题，例如头部相对身体过大／手挡住门襟／表情过强〕，以〔对应原参考中可见的事实〕为准。保留已正确的〔身份、衣服、构图等〕；维持〔原景别和规格〕。不引入新的姿势、服装或人物。

English:
> Use the original model [M], outfit [O], scene [S], and pose [ID] again. Correct only [observed issue, such as an oversized head relative to the body, a hand obscuring the placket, or an overly intense expression], following [visible evidence in the original reference]. Preserve the correct [identity, clothing, composition, and other verified elements], keeping [original framing and dimensions]. Do not introduce another pose, outfit, or person.

修复提示词不能替代结果检查。原图缺少所需身体信息时，先选择有支持的景别或补充必要参考；不要用模板编造缺失细节。
