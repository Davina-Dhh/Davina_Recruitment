# -*- coding: utf-8 -*-
"""TalentRadar / Davina · 投递画像与公司池

- scrape_keys: 已接入 Hiring-Radar、可自动拉岗
- wishlist: 期望覆盖但尚未自动拉岗（仅官网/待接入）
- seed_track_tags: 从 companies.seed 的「赛道」字段自动归入本赛道的额外公司
"""

YRD_LOCATIONS = [
    "上海", "杭州", "苏州", "南京", "宁波", "无锡", "嘉兴",
    "常州", "绍兴", "湖州", "南通", "扬州", "镇江", "合肥",
    "江浙沪", "长三角", "浦东", "徐汇", "闵行", "松江", "余杭", "滨江",
]

CLERICAL_KEYWORDS = "行政,文员,助理,秘书,人事,HR,财务,出纳,前台,运营,商务助理,综合管理,职能"

# Agent 工作流（静态蓝图 + 运行时可回放）
# role: 这一步在 Agent 里扮演什么；tools: 实际调用的能力；detail: 展开说明
AGENT_PIPELINE = [
    {
        "id": "listen",
        "name": "听懂目标",
        "desc": "赛道 · 地点 · 关键词",
        "role": "意图理解",
        "tools": ["画像赛道", "关键词解析", "地点策略"],
        "detail": "把侧栏选择编译成检索意图：查哪类公司、匹配哪些词、是否限制江浙沪、是否只看近 N 天。",
    },
    {
        "id": "choose",
        "name": "选择信息源",
        "desc": "公司路由 / ATS 匹配",
        "role": "路由规划",
        "tools": ["公司池", "LOCAL_PARSERS", "门户识别"],
        "detail": "根据公司 key 找到对应 ATS（飞书 / Moka / 北森）与门户参数；未接入的公司只能登记或粘贴门户后接入。",
    },
    {
        "id": "fetch",
        "name": "自动取岗",
        "desc": "调用 ATS 解析器",
        "role": "数据采集",
        "tools": ["feishu.py", "moka.py", "beisen.py", "subprocess"],
        "detail": "对每个目标公司启动对应解析脚本，拉取原始岗位列表（标题、地点、链接、JD 等）。",
    },
    {
        "id": "judge",
        "name": "判断匹配",
        "desc": "关键词 · 地点 · 时效",
        "role": "过滤推理",
        "tools": ["关键词过滤", "江浙沪规则", "近 N 天"],
        "detail": "在原始结果上做多层过滤：关键词命中 → 可选地点收窄 → 可选时效裁剪，再补全官网链接。",
    },
    {
        "id": "ai",
        "name": "AI 点评",
        "desc": "Agnes 匹配解读",
        "role": "大模型推理",
        "tools": ["Agnes 2.5 Flash", "画像匹配", "投递建议"],
        "detail": "调用 Agnes API，结合你的画像对岗位打分：匹配点、缺口、是否建议投、下一步行动。",
    },
    {
        "id": "deliver",
        "name": "输出结果",
        "desc": "清单 · 感兴趣 · 导出",
        "role": "交付",
        "tools": ["岗位卡片", "感兴趣清单", "JSON/CSV"],
        "detail": "把命中岗位交给主栏浏览，支持加入感兴趣、改状态备注、导出本地文件。",
    },
]

BRAND_NAME = "TalentRadar"
BRAND_CN = "智能招聘情报 Agent"
BRAND_EN = "TALENTRADAR"
BRAND_DAVINA = "Davina"
BRAND_FULL = "TalentRadar｜智能招聘情报 Agent"
BRAND_TAGLINE = "Davina 出品 · 多源拉岗 · Agent 可视 · AI 人岗 / 简历匹配"

TRACKS = {
    "半导体": {
        "desc": "芯片设计 / 制造 / 封测及相关",
        "scrape_keys": [
            "huahong", "cambricon", "biren", "3peak", "tecorigin",
            "brightchip", "icleague", "mthreads", "houmo", "carizon",
            "hesai", "wanji",
        ],
        "seed_track_tags": ["半导体", "GPU", "存算一体", "智驾芯片", "激光雷达"],
        "keywords": "产品,工艺,材料,质量,工艺工程师,产品经理,校招,管培",
        "wishlist": [
            {"name": "中芯国际", "city": "上海", "note": "待接入官方门户"},
            {"name": "华力微电子", "city": "上海", "note": "待接入"},
            {"name": "韦尔股份", "city": "上海", "note": "待接入"},
            {"name": "澜起科技", "city": "上海", "note": "待接入"},
        ],
    },
    "材料与车企": {
        "desc": "车企、汽零、新材料与高端制造",
        "scrape_keys": [
            "nio", "xpeng", "li", "tesla-cn", "geely", "yanfeng", "joyson",
            "bosch", "volvo", "chery", "leapmotor", "desaysv", "ecarx",
            "sanhua", "dreame", "voyah", "avatr", "zeron", "ecartech",
        ],
        "seed_track_tags": ["车厂", "汽车", "汽车零部件", "汽零", "新能源车", "新势力车企", "外企汽车", "电池"],
        "keywords": "产品,材料,质量,工艺,供应链,项目,校招,管培",
        "wishlist": [
            {"name": "上汽集团", "city": "上海", "note": "待接入"},
            {"name": "宁德时代", "city": "多地", "note": "待接入"},
            {"name": "宝钢/中国宝武", "city": "上海", "note": "待接入"},
        ],
    },
    "AI产品": {
        "desc": "大模型 / AI 应用产品（含上海人工智能实验室）",
        "scrape_keys": [
            "shlab", "zhipu", "moonshot", "minimax", "baichuan", "stepfun",
            "modelbest", "01ai", "smartmore", "juzibot", "sii",
            "bytedance", "shopee", "shengshu", "aisphere", "aibee",
            "infinigence", "meshy", "baai",
        ],
        "seed_track_tags": ["大模型", "AI", "AIInfra", "AI视频", "AIAgent", "AI投研", "AI科研", "AI安全", "AI3D"],
        "keywords": "产品,产品经理,AI产品,应用,解决方案,校招,管培,运营",
        "wishlist": [
            {"name": "商汤科技", "city": "上海", "note": "待接入"},
            {"name": "依图", "city": "上海", "note": "待接入"},
            {"name": "云从科技", "city": "上海等", "note": "待接入"},
        ],
    },
    "药企医疗": {
        "desc": "生物医药 / 医疗健康",
        "scrape_keys": ["wantai", "gstzy", "bayer"],
        "seed_track_tags": ["生物医药", "医疗", "外企"],
        "keywords": "产品,注册,质量,临床,医学,市场,管培,校招,行政",
        "wishlist": [
            {"name": "恒瑞医药", "city": "江苏/上海", "url": "https://job.hsrpharma.com/apply"},
            {"name": "复星医药", "city": "上海", "url": "https://www.fosunpharma.com/career/"},
            {"name": "百济神州", "city": "上海等", "url": "https://www.beigene.com.cn/careers/"},
            {"name": "药明康德", "city": "上海/江浙", "url": "https://www.wuxiapptec.com/careers"},
            {"name": "君实生物", "city": "上海", "note": "待接入"},
            {"name": "迈瑞医疗", "city": "多地", "note": "待接入"},
        ],
        "portal_only": [
            {"name": "恒瑞医药", "city": "江苏/上海", "url": "https://job.hsrpharma.com/apply"},
            {"name": "复星医药", "city": "上海", "url": "https://www.fosunpharma.com/career/"},
            {"name": "百济神州", "city": "上海等", "url": "https://www.beigene.com.cn/careers/"},
            {"name": "药明康德", "city": "上海/江浙", "url": "https://www.wuxiapptec.com/careers"},
        ],
    },
    "化妆品日化": {
        "desc": "美妆 / 日化 / 个护",
        "scrape_keys": ["pg", "smoore", "anker"],
        "seed_track_tags": ["快消", "雾化", "消费电子"],
        "keywords": "产品,配方,市场,品牌,运营,管培,校招,行政",
        "wishlist": [
            {"name": "上海家化", "city": "上海", "url": "https://www.jahwa.com.cn/"},
            {"name": "珀莱雅", "city": "杭州", "url": "https://www.proya.com/"},
            {"name": "逸仙电商(完美日记)", "city": "上海/广州", "url": "https://www.yatsenholdings.com/"},
            {"name": "欧莱雅中国", "city": "上海", "url": "https://careers.loreal.com/zh_CN/china"},
            {"name": "联合利华", "city": "上海", "url": "https://careers.unilever.com.cn/"},
            {"name": "自然堂/伽蓝", "city": "上海", "note": "待接入"},
            {"name": "林清轩", "city": "上海", "note": "待接入"},
        ],
        "portal_only": [
            {"name": "上海家化", "city": "上海", "url": "https://www.jahwa.com.cn/"},
            {"name": "珀莱雅", "city": "杭州", "url": "https://www.proya.com/"},
            {"name": "逸仙电商(完美日记)", "city": "上海/广州", "url": "https://www.yatsenholdings.com/"},
            {"name": "欧莱雅中国", "city": "上海", "url": "https://careers.loreal.com/zh_CN/china"},
            {"name": "联合利华", "city": "上海", "url": "https://careers.unilever.com.cn/"},
        ],
    },
    "文职职能": {
        "desc": "跨行业职能岗（行政 / 人事 / 财务 / 运营助理）",
        "scrape_keys": [
            "nio", "xpeng", "li", "pg", "bosch", "volvo", "huahong",
            "cambricon", "wantai", "zte", "eastmoney", "shopee", "marriott",
            "nestle", "ey", "kpmg",
        ],
        "seed_track_tags": [],
        "keywords": CLERICAL_KEYWORDS,
        "wishlist": [],
    },
}

DEFAULT_TRACK = "AI产品"
DEFAULT_LOCATION_MODE = "江浙沪优先"
DEFAULT_QUERY_MODE = "单公司精查"
