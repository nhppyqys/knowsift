# 做短剧并赚钱：经过过滤的知识地图

> 本文件由 KnowSift 根据逐条证书生成。未准入内容不会出现在知识结论中。

## 要回答的问题

B站和YouTube上的短剧教程中，哪些是可复用知识，哪些只是经验、营销承诺或待验证假设？

## 材料边界

检索日为2026-08-21。包含5个B站创作者页面、1个YouTube创作者视频、YouTube与B站官方规则、国家广电总局文件、StudioBinder制作指南及DramaBox日本创作者页面。网页内容按短摘录或结构化事实捕获；没有获得完整视频字幕的内容只用于确认标题、简介或发布者主张。

## 编译结果概览

| 状态 | # |
|---|---:|
| 有证据支持的知识 | 17 |
| 有条件成立的知识 | 0 |
| 原说法中可以保留的部分 | 0 |
| 从业者经验、观点与个人叙述 | 5 |
| 存在争议或证据不足的说法 | 3 |
| 被排除的说法 | 2 |

## 有证据支持的知识

### 短片前期计划的三份基础文件是剧本、拍摄计划和预算。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** 权威制作指南明确列出三份基础文件。
- **来源：** `GUIDE-STUDIOBINDER-2025`
- **局限：**
  - 这是通用短片前期框架，不等于短剧题材与商业成功公式。
- **证书：** `certificates/SD-PROD-001.json`

### 短片前期制作包括拆分剧本、准备镜头清单或分镜、排期、组建演员与团队以及落实场地。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** 权威制作指南逐项列出这些前期任务。
- **来源：** `GUIDE-STUDIOBINDER-2025`
- **局限：**
  - AI流程可以替换部分执行工具，但不会自动消除计划、版权和质量控制。
- **证书：** `certificates/SD-PROD-002.json`

### YouTube完整广告分成门槛可以通过一千订阅加近十二个月四千小时公开观看时长，或一千订阅加近九十天一千万次有效Shorts公开观看达到。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方YPP页面给出完整广告分成门槛。
- **来源：** `YT-YPP-ELIGIBILITY`
- **适用条件：**
  - 频道仍需通过政策审核。
- **局限：**
  - 达到数字门槛不保证申请通过，也不保证收入水平。
- **证书：** `certificates/SD-YT-001.json`

### YouTube合作伙伴的观看页广告净收入分成为百分之五十五。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方收益说明给出观看页广告分成比例。
- **来源：** `YT-REVENUE-SHARES`
- **适用条件：**
  - 需要加入YPP并接受对应模块。
- **局限：**
  - 实际收入取决于有效观看、地区、广告需求等因素。
- **证书：** `certificates/SD-YT-002.json`

### YouTube合作伙伴获得分配后Shorts收入的百分之四十五。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方收益说明给出Shorts分配后收入比例。
- **来源：** `YT-REVENUE-SHARES`
- **适用条件：**
  - 先按Creator Pool规则分配，再应用45%比例。
- **局限：**
  - 45%不是每次播放的固定单价。
- **证书：** `certificates/SD-YT-003.json`

### YouTube合作伙伴的粉丝资助净收入分成为百分之七十。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方收益说明给出粉丝资助净收入比例。
- **来源：** `YT-REVENUE-SHARES`
- **适用条件：**
  - 需要满足相应功能资格并接受Commerce Product Module。
- **局限：**
  - 粉丝是否付费取决于真实受众关系。
- **证书：** `certificates/SD-YT-004.json`

### YouTube把批量生产或重复内容归为不真实内容，并规定这类内容不符合变现条件。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方频道变现政策直接规定批量、重复内容不符合变现要求。
- **来源：** `YT-MONETIZATION-POLICY`
- **局限：**
  - 使用AI本身不是问题，模板化、低差异和缺少原创价值才是关键风险。
- **证书：** `certificates/SD-YT-005.json`

### YouTube要求披露看起来真实的AI生成内容或经过实质性AI修改的内容。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方AI披露规则要求披露逼真或实质性修改内容。
- **来源：** `YT-AI-DISCLOSURE`
- **适用条件：**
  - 适用于看起来真实的生成或实质性修改内容。
- **局限：**
  - 仍需同时遵守版权、社区与广告友好规则。
- **证书：** `certificates/SD-YT-006.json`

### 在YouTube正确披露AI内容本身不会限制该内容的变现资格。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** YouTube官方说明确认正确披露本身不降低变现资格。
- **来源：** `YT-AI-DISCLOSURE`
- **局限：**
  - 不代表该内容自动符合其他变现政策。
- **证书：** `certificates/SD-YT-007.json`

### B站充电计划允许用户在充电面板支付B币支持UP主。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** B站官方充电协议确认了观众直接支持渠道。
- **来源：** `BILI-CHARGE-RULES`
- **适用条件：**
  - UP主需开通充电计划并满足平台流程。
- **局限：**
  - 存在功能不等于观众会付费。
- **证书：** `certificates/SD-BILI-001.json`

### 参与B站充电计划的UP主应拥有发布内容的合法权利或全部合法授权。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** B站官方协议明确要求合法权利或完整授权。
- **来源：** `BILI-CHARGE-RULES`
- **局限：**
  - 具体素材还可能涉及音乐、字体、肖像、声音和AI训练/生成条款。
- **证书：** `certificates/SD-BILI-002.json`

### B站花火当前要求实名认证且年满十八岁、粉丝不少于一万、近三十天发布过原创视频，并达到规定的电磁力分数。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** B站官方花火FAQ列出当前入驻条件。
- **来源：** `BILI-HUAHUO-FAQ`
- **适用条件：**
  - 规则会变化，应在接单前重新核对。
- **局限：**
  - 入驻只是获得商单工具资格，不保证获得订单。
- **证书：** `certificates/SD-BILI-003.json`

### 在中国境内由网络视听平台、小程序或投流方播出、引流或推送的微短剧须持有网络剧片发行许可证或完成相应上线报备登记程序。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** 国家广电总局官方通知给出当前上线前审核备案要求。
- **来源：** `NRTA-NOTICE-2025`
- **适用条件：**
  - 适用于中国境内网络微短剧传播。
- **局限：**
  - 不同投资规模与传播方式对应的申报层级不同。
- **证书：** `certificates/SD-CN-001.json`

### 《微短剧发展管理办法》规定未取得发行许可证、批准文件或节目编号的微短剧不得播出。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** 已公布的部门规章给出许可证、批准文件或节目编号要求。
- **来源：** `NRTA-MEASURES-2026`
- **适用条件：**
  - 该办法自2026-09-01起施行。
- **局限：**
  - 申报类别和实施细则需要结合项目所在地与播出平台确认。
- **证书：** `certificates/SD-CN-002.json`

### 《微短剧发展管理办法》自二〇二六年九月一日起施行。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** 国家广电总局正式公布了施行日期。
- **来源：** `NRTA-MEASURES-2026`
- **局限：**
  - 本案例检索日是2026-08-21，施行日尚未到。
- **证书：** `certificates/SD-CN-003.json`

### DramaBox日本创作者页面接受十五至一百集的短剧作品进行分发洽谈。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** DramaBox日本官方创作者页面给出接收的集数范围。
- **来源：** `DRAMABOX-JP-CREATORS`
- **适用条件：**
  - 仅代表该日本站页面与洽谈入口。
- **局限：**
  - 提交样片不等于签约或上线。
- **证书：** `certificates/SD-DIST-001.json`

### DramaBox日本创作者页面所述的基本收益方式是最低保底加收入分成，具体条件以合同为准。

- **状态：** `SUPPORTED_KNOWLEDGE`
- **为什么这样分类：** DramaBox日本官方页面说明基本收益结构。
- **来源：** `DRAMABOX-JP-CREATORS`
- **适用条件：**
  - 具体比例、费用、独占性和权利范围以合同为准。
- **局限：**
  - MG并非所有项目都必然获得的固定收入。
- **证书：** `certificates/SD-DIST-002.json`


## 从业者经验、观点与个人叙述

### B站创作者把画面、运镜、景别、时长、台词、声音、转场和道具列为拍摄脚本字段。

- **状态：** `PRACTICE_OR_VIEWPOINT`
- **为什么这样分类：** 证书只确认该B站创作者给出了这组脚本字段。
- **来源：** `BILI-STORYBOARD`
- **局限：**
  - 这是实务模板，不是唯一正确格式。
- **证书：** `certificates/SD-VIEW-001.json`

### B站教程发布者把短剧推广描述为授权后剪辑片段并发布，为指定应用拉新以赚取佣金。

- **状态：** `PRACTICE_OR_VIEWPOINT`
- **为什么这样分类：** 证书只确认发布者这样描述短剧推广模式。
- **来源：** `BILI-PROMOTION-TUTORIAL`
- **适用条件：**
  - 发布者明确提到先取得授权。
- **局限：**
  - 佣金规则、平台资格和实际转化率未被独立核验。
- **证书：** `certificates/SD-VIEW-002.json`

### B站视频发布者自述每天花一小时做海外短剧推广，当月多赚二千三百元以上。

- **状态：** `PRACTICE_OR_VIEWPOINT`
- **为什么这样分类：** 证书只确认发布者做过该收入自述。
- **来源：** `BILI-EARNING-2300`
- **局限：**
  - 没有核验成本、失败样本、账号基数和后台原始数据。
- **证书：** `certificates/SD-VIEW-003.json`

### D4Darious的视频简介称该视频讨论短片写作中的背景故事管理和应避免的问题。

- **状态：** `PRACTICE_OR_VIEWPOINT`
- **为什么这样分类：** 证书只确认YouTube视频简介声明了这些讨论内容。
- **来源：** `YT-D4DARIOUS-TIPS`
- **局限：**
  - 没有完整字幕，因此不把具体建议扩写成知识。
- **证书：** `certificates/SD-VIEW-004.json`

### B站视频发布者提醒短剧版权剪辑、分红和投资项目中存在骗局风险。

- **状态：** `PRACTICE_OR_VIEWPOINT`
- **为什么这样分类：** 证书只确认发布者发出了骗局风险提醒。
- **来源：** `BILI-SCAM-WARNING`
- **局限：**
  - 不能据此认定某个具体项目违法或诈骗。
- **证书：** `certificates/SD-VIEW-005.json`


## 存在争议或证据不足的说法

### 零基础用户学完一套AI短剧教程即可接单变现。

- **状态：** `DISPUTED_OR_UNRESOLVED`
- **为什么这样分类：** 唯一依据是带资料导流和变现承诺的课程营销页面。
- **来源：** `BILI-AI-COURSE`
- **局限：**
  - 缺少真实订单、报价、获客成本、交付能力和失败率。
- **证书：** `certificates/SD-HOLD-001.json`

### 短剧推广适合普通新手稳定月入二万元以上。

- **状态：** `DISPUTED_OR_UNRESOLVED`
- **为什么这样分类：** 唯一依据是收入承诺型视频标题。
- **来源：** `BILI-EARNING-20K`
- **局限：**
  - 缺少样本范围、时间成本、投流成本、账号存活率和后台数据。
- **证书：** `certificates/SD-HOLD-002.json`

### 普通人每天花一小时做海外短剧推广都能月赚二千三百元以上。

- **状态：** `DISPUTED_OR_UNRESOLVED`
- **为什么这样分类：** 一个人的自述不能外推到普通人。
- **来源：** `BILI-EARNING-2300`
- **局限：**
  - 需要多账号、完整成本与时间窗口的可审计记录。
- **证书：** `certificates/SD-HOLD-003.json`


## 被排除的说法

### 无需获得版权或授权也可以剪辑他人短剧并在B站发布获利。

- **状态：** `REJECTED`
- **为什么这样分类：** B站官方协议与“无需授权”的说法直接冲突。
- **来源：** `BILI-CHARGE-RULES`
- **局限：**
  - 其他平台和素材类型还需要核对各自授权条款。
- **证书：** `certificates/SD-REJECT-001.json`

### 批量生成重复模板化AI短剧就能稳定通过YouTube频道变现审核。

- **状态：** `REJECTED`
- **为什么这样分类：** YouTube官方政策与“模板化批量内容稳定通过变现”的说法直接冲突。
- **来源：** `YT-MONETIZATION-POLICY`
- **局限：**
  - 原创、内容差异和观众价值仍需要人工与平台审核。
- **证书：** `certificates/SD-REJECT-002.json`

## 仍未解决的问题

- B站与YouTube短剧账号在不同题材、地区和时长下的真实RPM、完播率和付费率分布是什么？
- 专业短剧平台对独立创作者的签约率、MG范围、分账周期和回本率是什么？
- 真人短剧与AI短剧在相同剧本和投放条件下的完播、复看、获客成本和制作成本如何比较？
- 短剧推广项目的授权链、结算后台、退款与封号率能否获得可审计样本？

## 来源清单

| 来源 ID | 标题 | 性质 | 载体 | 位置 |
|---|---|---|---|---|
| `GUIDE-STUDIOBINDER-2025` | Making a Short Film — Pre Production Workflow Step-by-Step | `AUTHORITATIVE_GUIDANCE` | `ARTICLE` | https://www.studiobinder.com/blog/making-short-film-pre-production/ |
| `YT-D4DARIOUS-TIPS` | How to Make A Short Film: Important Tips and Advice | `EXPERT_INTERPRETATION` | `VIDEO` | https://www.youtube.com/watch?v=PalEaciHvXI |
| `BILI-STORYBOARD` | 拍摄视频第一步：了解视频创作与分镜脚本设计 | `EXPERT_INTERPRETATION` | `ARTICLE` | https://www.bilibili.com/opus/602498179786822057 |
| `BILI-AI-COURSE` | AI短剧：剧本、分镜、人物、视频、配音、剪辑全流程 | `MARKETING` | `VIDEO` | https://www.bilibili.com/video/BV1n3Vz6LEVS/ |
| `BILI-PROMOTION-TUTORIAL` | 短剧推广项目：授权、收益、流程、剪辑和发布 | `EXPERT_INTERPRETATION` | `VIDEO` | https://www.bilibili.com/video/BV1QryeBtEGv/ |
| `BILI-EARNING-2300` | 实测月赚2k+：海外短剧推广 | `ANECDOTE` | `VIDEO` | https://www.bilibili.com/video/BV1NahvzTEYn/ |
| `BILI-EARNING-20K` | 短剧推广项目拆解：小白也可以月入2w+ | `MARKETING` | `VIDEO` | https://www.bilibili.com/video/BV1Wr421H7oz/ |
| `BILI-SCAM-WARNING` | 短剧版权剪辑骗局与短剧分红资金盘骗局 | `OPINION` | `VIDEO` | https://www.bilibili.com/video/BV1rwdjBHEdE/ |
| `YT-YPP-ELIGIBILITY` | YouTube Partner Program overview and eligibility | `OFFICIAL_DOCUMENTATION` | `ARTICLE` | https://support.google.com/youtube/answer/72851 |
| `YT-REVENUE-SHARES` | YouTube partner earnings overview | `OFFICIAL_DOCUMENTATION` | `ARTICLE` | https://support.google.com/youtube/answer/72902 |
| `YT-MONETIZATION-POLICY` | YouTube channel monetization policies | `OFFICIAL_DOCUMENTATION` | `ARTICLE` | https://support.google.com/youtube/answer/1311392 |
| `YT-AI-DISCLOSURE` | Disclosing use of GenAI content | `OFFICIAL_DOCUMENTATION` | `ARTICLE` | https://support.google.com/youtube/answer/14328491 |
| `BILI-CHARGE-RULES` | 哔哩哔哩充电计划用户协议 | `OFFICIAL_DOCUMENTATION` | `DOCUMENT` | https://www.bilibili.com/blackboard/charge-privacy.html |
| `BILI-HUAHUO-FAQ` | 花火商单平台UP主入驻常见问题 | `OFFICIAL_DOCUMENTATION` | `DOCUMENT` | https://www.bilibili.com/blackboard/activity-zWUGlzmXPK.html |
| `NRTA-NOTICE-2025` | 关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知 | `OFFICIAL_DOCUMENTATION` | `DOCUMENT` | https://www.nrta.gov.cn/art/2025/2/5/art_113_70148.html |
| `NRTA-MEASURES-2026` | 微短剧发展管理办法 | `OFFICIAL_DOCUMENTATION` | `DOCUMENT` | https://www.nrta.gov.cn/art/2026/7/31/art_1588_73827.html |
| `DRAMABOX-JP-CREATORS` | DramaBox短剧征集与分发说明 | `OFFICIAL_DOCUMENTATION` | `ARTICLE` | https://www.dramabox.jp/creators |
