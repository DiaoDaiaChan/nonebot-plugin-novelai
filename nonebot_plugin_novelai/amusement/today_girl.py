from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Bot, ActionFailed

from ..backend import AIDRAW
from ..extension.translation import translate_deepl, translate
from ..config import config
from ..utils.data import basetag, lowQuality

import random, time, json, re

today_girl = on_command("二次元的我")

# 以下代码来自
# tags大部分来自幻术魔导书

pose_dict = {'站立': 'standing', '单脚站立': 'standing on one leg', 'S型曲线站立': 'contrapposto', '弯腰': 'bent over', '屈膝礼': 'curtsy', '躺着': 'lying', '躺下': 'lying down', '仰卧': 'on back', 
             '侧卧': 'lying on side', '趴着': 'crawling', '趴着翘臀': 'top-down bottom-up', '坐': 'sitting', '鸭子坐': 'wariza', '坐在地上': 'sitting on the ground', 
             '正坐': 'seiza', '姐坐': 'yokozuwari', '印度盘腿': 'indian style', '莲花坐': 'lotus position', '跨坐': 'straddling', '靠在靠背上斜着坐': 'reclining', '跨坐大腿': 'thigh straddling', 
             '二郎腿': 'figure four sitting', '跪': 'on knees', '单膝跪': 'one knee', '身体倾斜': 'leaning', '靠在一边': 'leaning to the side', '身体前倾': 'leaning forward', '身体后倾': 'leaning back', 
             '靠在物体上': 'leaning on object', '手倒立': 'handstand', '头倒立': 'headstand', '颠倒的': 'upside-down', '凹造型': 'posing', '战斗姿势': 'fighting stance', '拔刀起手式': 'battoujutsu stance', 
             '那个姿势': 'the pose', '僵尸姿势': 'zombie pose', '兔耳姿势': 'bunny pose', '抬高手臂上指': 'kamina pose', '三点着地': 'superhero landing', '焦糖舞': 'caramelldansen', '叉腰向上指': 'saturday night fever', 
             '蝎子姿势': 'scorpion pose', '歪头': 'head tilt', '低头': 'head down', '头后仰': 'head back', '脸贴地面': 'faceplant', '蹲': 'squatting', '四肢着地': 'all fours', '胎儿姿势': 'fetal position', 
             '失意体前屈': 'prostration', '抱腿': 'leg hug', '胸放桌上': 'breasts rest on table', '伸展': 'stretch', '竖一字马': 'standing split', '转身': "turn one's back", '弓身': 'arched back', '卡在墙里': 'through wall', 
             '漂浮': 'floating', '浮在水上': 'afloat', '保持平衡': 'balancing', '背着': 'piggyback', '拍打(翅膀)': 'flapping', '盯着': 'staring', '手臂在头后': 'arms behind head', 
             '手臂在背后': 'arms behind back', '伸直双臂': 'outstretched arms', '伸出单臂': 'outstretched arm', '伸出手': 'outstretched hand', '双手垂放': 'arms at sides', '单抬臂': 'arm up', '双抬臂': 'arms up', 
             '张手': 'spread arms', '用手支撑住': 'arm support', '手交叉于胸前': 'arms crossed', '交叉双臂': 'crossed arms', '手臂后拉': 'arm held back', '遮住关键部位的手臂': 'convenient arm', 
             '手臂摆出心姿势': 'heart arms', '翘大拇指': 'thumbs up', '食指抬起': 'index finger raised', '猫爪': 'cat pose', '指枪': 'finger gun', '虎爪': 'claw pose', '爪子': 'paw pose', '狐狸手势': 'fox shadow puppet', 
             'V手势': 'peace hand', '胜利手势': 'victory pose', 'v在嘴上': 'v over mouth', '九字印': 'kuji-in', '嘘手势': 'shushing', '伸小拇指': 'pinky out', '指尖抵指间': 'steepled fingers', '比中指': 'middle finger', 
             '握拳': 'fist', '攥拳': 'clenched hands', '举起拳头': 'raised fist', '紧张手势': 'fidgeting', '舔手指': 'finger to mouth', '双手相扣': 'own hands clasped', '双手相合': 'own hands together', '张开双手': 'open hands', 
             '张开手': 'open hand', '双手比心': 'heart hands', '手杯': 'cupping hands', '爽手势': 'shocker', '用手指比数字': 'finger counting', '兰花指': 'orchid fingers', '手在头发里': 'hand in hair', '手放嘴上': 'hand to own mouth', 
             '手放脸上': 'hand on own face', '双手放脸': 'hands on own face', '手放帽子上': 'hand on headwear', '手放自己头上': 'hand on own head', '手放耳朵': 'hand on ear', '手放前额': 'hand on own forehead', '手放下颚': 'hand on own chin', 
             '手放脸颊': 'hand on own cheek', '手放脖子': 'hand on own neck', '手放肩上': 'hand on own shoulder', '手放胸部': 'hand on own chest', '手放肚子': 'hand on own stomach', '手放臀部': 'hand on own ass', '双手放臀部': 'hands on ass', 
             '手放膝盖': 'hand on own knee', '双手放膝盖': 'hands on own knees', '手在大腿间': 'hand between legs', '双手放脚': 'hands on feet', '手插兜': 'hand in pocket', '双手插兜': 'hands in pockets', '手在内裤里': 'hand in panties', 
             '单手叉腰': 'hand on hip', '双手叉腰': 'hands on hips', '拨头发': 'hair flip', '拉头发': 'hair pull', '撩头发': 'hair tucking', '札头发': 'tying hair', '梳头': 'hairdressing', '卷头发': 'hair twirling', 
             '扎辫子': 'bunching hair', '捏着帽檐': 'hat tip', '提裙': 'skirt hold', '拉起自己衣服': 'lifted by self', '拉起衣服': 'clothes lift', '拉起连衣裙': 'dress lift', '拉下连衣裙下摆': 'dress tug', '胸罩拉到胸上方': 'bra lift', 
             '拉着吊带': 'holding strap', '整理裤袜': 'adjusting legwear', '抓着领带': 'necktie grab', '拨内裤': 'adjusting panties', '拉起和服': 'kimono lift', '抱着枕头': 'pillow hug', '抱着某物': 'object hug', '揉眼睛': 'rubbing eyes', 
             '遮住耳朵': 'covering ears', '抱自己腿': 'hugging own legs', '捏着肚子': 'belly grab', '搅拌': 'whisking', '投掷': 'pitching', '带着': 'carrying', '拿着长枪': 'polearm', '扶眼镜': 'adjusting eyewear', '伸手触及': 'reaching', 
             '打结': 'tying', '指向': 'pointing', '指向观众': 'pointing at viewer', '指向上': 'pointing up', '指向下': 'pointing down', '指向前': 'pointing forward', '展示腋下': 'presenting armpit', '展示内裤': 'presenting panties', '遮着裆部': 'covering crotch', 
             '托腮': 'chin rest', '托颊': 'head rest', '托胸': 'breast hold', '挥手': 'waving', '敬礼': 'salute', '二指敬礼': 'two-finger salute', '瓦肯举手礼': 'vulcan salute', '拿着': 'holding', '力量拳头': 'power fist', '抱着我手势': 'carry me', '皮影戏': 'shadow puppet'}

hairstyle_dict = {
    '发色': '<color>hair', '渐变色': 'gradient colour', '渐变发': 'gradient hair', 
    '条纹头发(挑染)': 'streaked hair ', '金发': 'blonde hair', '多彩头发': 'multicolored hair', 
    '内侧染色': 'colored inner hair', '彩虹发': 'rainbow hair', '超短发': 'very short hair', '短发': 'short hair', 
    '中等长发': 'medium hair', '长发': 'long hair', '超长发': 'very long hair', '极长发': 'absurdly long hair', '披肩发': 'hair over shoulder', 
    '刘海': 'bangs', '不对称刘海': 'asymmetrical bangs', '齐刘海': 'blunt bangs', '单侧齐刘海': 'side blunt bangs', '遮眼刘海': 'hair over eyes', 
    '遮单眼刘海': 'hair over one eye', '分刘海': 'parted bangs', '长刘海': 'long bangs', '扫刘海': 'swept bangs', '朝一个方向的刘海': 'side swept bangs', 
    '斜刘海': 'diagonal bangs', '眼间发': 'hair between eyes', '交错刘海': 'crossed bangs', '大背头': 'hair slicked back', '半遮眼': 'jitome', 
    '掀起的刘海': 'bangs pinned back', '耳前侧发': 'sidelocks', '耳后发': 'hair behind ear', '公主卷': 'drill hair', '单钻头卷': 'side drill', 
    '双钻头卷': 'twin drills', '四钻头卷': 'quad drills', '进气口(侧发顶部竖起)': 'hair intakes', '单侧进气口': 'single hair intake', 
    '侧发后梳': 'half updo', '垂下的长卷发': 'ringlets', '辫子': 'braid', '长辫': 'long braid', '刘海辫': 'braided bangs', '单侧辫': 'side braid', 
    '双侧辫': 'side braids', '单辫': 'single braid', '双辫': 'twin braids', '低双辫': 'low twin braids', '三股辫': 'tri braids', '四股辫': 'quad braids', 
    '多辫': 'multiple braids', '法式 辫': 'french braid', '冠型织辫': 'crown braid', '前辫': 'front braid', '脏辫': 'dreadlocks', '低辫长发': 'low-braided long hair', 
    '发髻/包子头': 'hair bun', '丸子头': 'topknot', '发髻辫': 'braided bun', '双发髻': 'double bun', '三发髻': 'triple bun', '侧发髻': 'side bun', '锥形发髻': 'cone hair bun', 
    '甜甜圈发髻': 'doughnut hair bun', '飞仙髻': 'hair rings', '单发圈': 'single hair ring', '马尾': 'ponytail', '高马尾': 'hair one side up', '低马尾': 
    'low ponytail', '短马尾': 'short ponytail', '侧马尾': 'side ponytail', '双马尾': 'twintails', '低双马尾': 'low twintails', ' 短双马尾': 'short twintails', '高双马尾': 'hair two side up', 
    '不对称双马尾': 'uneven twintails', '马尾辫': 'braided ponytail', '折叠马尾': 'folded ponytail', '分开的单马尾': 'split ponytail', '波波头': 'bob cut', '公主切': 'hime cut', '蘑菇头': 'bowl cut', 
    '帽盔头': 'undercut', '蓬帕杜发型': 'pompadour', '莫霍克发型': 'mohawk', '爆炸头': 'afro', '超大爆炸头': 'huge afro', '精灵头': 'pixie cut', '蜂窝头': 'beehive hairdo', '平头': 'crew cut', '寸头': 'buzz cut', 
    '鲻鱼头': 'mullet', '波浪发(自然卷)': 'wavy hair', '直发': 'straight hair', '卷发': 'curly hair', '刺发': 'spiked hair', '外卷发': 'flipped hair', '呆毛': 'ahoge', '大呆毛': 'huge ahoge', 
    '多呆毛(天线)': 'antenna hair', '心形呆毛': 'heart ahoge', '蝴蝶结状头发': 'bow-shaped hair', '头发很多': 'big hair', '秃头': 'bald', '秃头女孩': 'bald girl', '凌乱头发': 'messy hair', 
    '散发': 'hair spread out', '漂浮头发': 'floating hair', '湿头发': 'wet hair', '嘴里有头发': 'hair in mouth', '有光泽的头发': 'shiny hair', '摆动的头发': 'hair flaps', '扎起的头发': 'tied hair', 
    '多扎头发': 'multi-tied hair', '一缕一缕的头发': 'hair strand', '非对称发型': 'asymmetrical hair', '富有表现力的头发': 'expressive hair', '瀑布发型': 'curtained hair', '美人尖': "widow's peak", 
    '触手头发': 'tentacle hair', '孤颈毛': 'lone nape hair', '丁髷': 'chonmage'
}

race_list = ['兽耳', '兽耳绒毛', '兽耳', '蝙蝠耳', '猫耳', '狗耳', '狐耳', '兔耳', 
 '兔耳', '浣熊耳', '老鼠耳', '松鼠耳', '熊耳', '虎耳', '狼耳', '马耳', 
 '牛耳', '羊耳', '山羊耳', '狮耳', '熊猫耳', '鹿耳', '猴耳', '猪耳', 
 '鼬耳', '羊驼耳', '尖耳', '长尖耳', '垂耳', '机械耳', '皮卡丘耳', 
 '角', '龙角', '山羊角', '牛 角', '鹿角', '恶魔角', '', '']

data_dict = {
    "date": "true",
    "parts": {
        "facestyle": ['可爱脸', '动漫脸', '大额头', '额头记号', '额前宝石', '眼睛疤痕', '头发后的眉毛', '短眉毛', 
                      '粗眉毛', '男性俊眉', '虎牙', '上牙', '尖牙', '圆齿', '牙齿', '舌头', '唾液', '泪痣', '美人痣', 
                      '浓妆', '胡须', '面纹', '脸上疤痕', '微笑', '大笑', '咧嘴笑', '露齿', '邪笑', '沾沾自喜的', '诱人的微笑', 
                      '顽皮的脸', '眉毛翘起', '愤怒', '愤怒', '恼火', '噘嘴', '小皱眉', '中皱眉', '大皱眉', '眉毛下垂', '哭泣', 
                      '哭', '眼泪', '哭的撕心裂肺', '泪如雨下', '眼含泪水的', '沮丧', '绝望', '惊讶', '惊恐', '尖叫', '小尖叫', 
                      '吓得变色了', '慌张', '紧张出大量的汗', '慌张出汗', '紧张', '脸红', '尴尬', '害羞', '无聊', '困倦', '哈欠', 
                      '精疲力竭的', '喝醉的', '无表情', '困惑', '蔑视', '情绪异常激动的', '狂气', '伸出舌头', '喷嚏', '波形嘴', 
                      '猫嘴', '方嘴', '嘴唇微开', '张嘴', '闭嘴', '半闭眼', '闭单眼', '闭单眼', '闭眼', '闭眼', '空洞注视'],
        "height": ["连衣裙", "半身裙", "迷你裙", "长裙", "短裙", "牛仔裙", "针织裙", "花裙", "雪纺裙", "荷叶边裙",
                 "蕾丝裙", "吊带裙", "背心裙", "打底裙", "百褶裙", "铅笔裙", "礼服裙", "晚礼服", "婚纱", "旗袍",
                 "唐装", "中山装", "短裤", "牛仔短裤", "运动短裤", "高腰短裤", "热裤", "背带短裤", "连体裤", "牛仔连体裤",
                 "运动连体裤", "背带裤", "西装裤", "哈伦裤", "运动裤", "休闲裤", "牛仔裤", "小脚裤", "阔腿裤", "直筒裤",
                 "七分裤", "九分裤", "短袖衬衫", "长袖衬衫", "牛仔衬衫", "卫衣", "T恤", "针织衫", "毛衣", "羽绒服",
                 "棉服", "夹克", "风衣", "大衣", "皮衣", "西装", "马甲", "短外套", "连帽衫", "毛呢大衣", "羊毛衫",
                 "皮草", "羊绒衫", "格子裙", "条纹裙", "波点裙", "花卉印花裙", "宽松连衣裙", "收腰连衣裙", "直筒连衣裙",
                 "A字连衣裙", "雪纺连衣裙", "蕾丝连衣裙", "抹胸裙", "荷叶边连衣裙", "旗袍裙", "百褶连衣裙", "花苞裤", 
                 "爆裂牛仔裤", "修身西装裤", "宽松哈伦裤", "铅笔裤", "针织长裤", "网纱长裙", "棉麻连衣裙", 
                 "印花雪纺裙", "背心吊带裙", "雪纺吊带裙", "收腰雪纺裙", "A字蕾丝裙", "金丝绒裙", "露脐上衣", 
                 "单肩上衣", "蝴蝶结上衣", "假两件上衣", "圆领T恤", "V领T恤", "长款毛衣", "短款毛衣", "连帽卫衣", 
                 "短袖针织衫", "长袖针织衫", "毛呢外套", "印花外套", "运动外套", "真皮外套", "大牌马甲", "衬衫裙", "高领毛衣", 
                 "短款皮衣", "牛仔夹克", "短款连帽卫衣", "高腰阔腿裤", "长款羽绒服", "半高领毛衣", "针织开衫", "阔腿裤套装", "短款风衣", 
                 "复古印花连衣裙", "西装外套", "宽松牛仔裤", "短袖针织衫", "半身长裤套装", "毛呢马甲", "蕾丝吊带上衣", "修身西装", "花边长袖衬衫", 
                 "高腰直筒裤", "长袖雪纺衫", "牛仔裤套装", "红色小西装", "衬衫连衣裙", "鱼尾裙", "收腰长款外套", "宽松卫衣", "牛仔长裤", "长袖碎花连衣裙", 
                 "修身休闲裤", "吊带背心", "半身半裙套装", "高腰直筒牛仔裤", "蕾丝短袖上衣", "百搭针织衫", "宽松连帽毛衣", "不规则半身裙", "牛仔连衣裙", "运动长裤",'比基尼', 
                 '系绳比基尼', '微小比基尼', '比基尼铠甲', '无肩带比基尼', '圣诞比基尼', '前系带比基尼', '侧边系带比基尼', '无罩杯比基尼', '泳衣', '连体泳衣', '学校泳衣',
                   '竞赛泳衣', '学校竞赛泳衣', '连衣裙', '短连衣裙', '露背连衣裙', '绕颈连衣裙', '毛衣连衣裙', '紧身连衣裙', '无袖连衣裙', '无吊带连衣裙', ' 荷叶边连衣裙', 
                   '蝉翼纱连衣裙', '格子连衣裙', '芭蕾连衣裙', '夏日长裙', '阿尔卑斯山少女装', '细致的哥特式束腰连衣裙', '太阳裙', '紧身衣', '无肩带紧身衣', '胶衣', '兔女郎紧身衣', 
                   '内层紧身衣', '水手服', '校服', '西装', '黑西装', '燕尾服', '女性西服', '运动服', '体操服', '排球服', '普通雨衣', '透明雨衣', '雨披', '睡袍', '睡衣', '性感睡衣', 
                   '围裙', '女仆围裙', '浴巾', '沙滩巾', '沙滩浴巾', '私服', '长袍', '连衫裤', '内衣', '女用贴身内衣裤', '猫系内衣', '绷带', '手臂带绷带', '手带绷带', '绑着绷带的脚', 
                   '裸体浴巾', '裸体围裙', '裸体工装', '裸体绑带', '女仆装', '修女服', '修道服', '短祭袍', '兜帽斗篷', '舞娘服', '戏服', '玩偶装', '鬼魂装', '木乃伊装', '吸血鬼装', 
                   '洛丽塔', '哥特洛丽塔', '和风洛丽塔', '汉服', '旗袍', '旗袍', '唐装', '和服', '着物', '浴衣', '羽织', '袴', '袴裙', '和服带', '圣诞装', '万圣节装', '婚纱', '丧服'],
        "hairstyle": list(hairstyle_dict.keys()),
        "daimao": list(pose_dict.keys()),
        "breastsize": ["DCUP", "惊天巨乳", "飞机场", "ECUP",
                        "BCUP", "ACUP", "CCUP", "GCUP", "FCUP"],
        "color": [
            ["黄色", "金色"], "深蓝色", "粉色", ["红色", "赤色"], ["白色", "银色"], "灰色",
            "绿色", "棕色", "橙色", "蓝色", "紫色", "彩虹色", "黑色"
        ],
        "haircolor": ["{color}", "白色",],
        "property": ['光', '正面光', '侧面光', '背光', '逆光', 
                     '黄金时段照明', '最佳照明', '闪光', '闪光', 
                     '镜头光晕', '过曝光', '电影光照', '戏剧光', 
                     '光线追踪', '精细光照', '漏光', '射线光束', 
                     '浮动光斑', '阳光', '太阳光束', '斑驳的阳光', 
                     '阳光透过树木', '月光', '圣光', '从上而下的光线', 
                     '发光', '荧光', '漂亮精细的发光', '反射', '涟漪', 
                     '云隙光', '晨光', '霓虹灯', '霓虹灯', '傍晚背对阳光', 
                     '明暗对比', '影', '阴影', '有影的', '最佳阴影', '强烈阴影', 
                     '强烈阴影', '戏剧阴影', '树影', '投下阴影', '眼部阴影'],
        "job": ['光环', '机械式光环', '耳饰', '耳环', '心形耳饰', 
                '月牙耳饰', '水晶耳饰', '耳机', '耳机(带话筒)', 
                '后脑带的耳机', '猫耳耳机', '眼镜', '太阳镜', '护目镜', 
                '眼镜在头上', '护目镜在头上', '带眼镜的', '无框眼镜', 
                '下半无框眼镜', '心形眼镜', '眼罩', '眼罩', '蒙上的眼', 
                '单眼绷带', '面具', '头上面具', '摘下的面具', '狐狸面具', 
                '天狗面具', '口罩', '医用口罩', '防毒面具', '面纱', '脸绷带', 
                'VR头显', '颈饰', '锚形项圈', '颈带', '围巾', '铃铛', '项圈', '狗项圈', 
                '项链', '珠子项链', '领结', '领带', '格子领带', '锁链', '拉丁十字架', '领巾', 
                '脖子挂耳机', '狗牌', '心锁', '脖子挂口哨', '手套', '肘部手套', '猫猫手套', 
                '无指手套', '猫爪', '乳胶手套', '手镯', '花手镯', '珠子手链', '手镯', '腕带', 
                '腕饰', '护腕', '臂章', '臂环', '臂环', '手铐', '手枷', '宽手铐', '腰带', '搭扣', 
                '武装带', '饰带', '大腿带', '腿部花边环', '腿带', '腿上创可贴', '绑脚', '腿部系带', 
                '脚环', '蝴蝶结', '格子蝴蝶结', '流苏', '丝带', '宝石', '钻石', '缎带', '花饰', 
                '徽章', '创可贴', '蓬莱玉枝', '发饰', '蝙蝠发饰', '青蛙发饰', '蛇发饰', '猫头饰', 
                '兔子头饰', '食物主题发饰', '南瓜发饰', '翅膀发饰', '星星发饰', '心形发饰', '蝴蝶发饰', 
                '树叶发饰', 'X发饰', '羽毛发饰', '月牙发饰', '锚发饰', '骷髅发饰', '音符发饰', '胡萝卜发饰', 
                '骨发饰', '雪花头饰', '三叶草发饰', '鱼形发饰', '发髻套', '扎发绒球', '头饰蝴蝶结', '多个蝴蝶结', 
                '发带', '发带', '发夹', '发卡', '头饰花', '发箍', '洛丽塔发箍', '蝴蝶结发箍', '发束', '发束', 
                '女仆头饰', '头纱', '新娘头纱', '花环', '花环', '头上铃铛', '发珠', '蓝牙耳机头饰', '簪子'],
        "background": ['花瓣', '花瓣', '玫瑰花瓣', '飞舞的花瓣', '落下的花瓣', '水面的花瓣', '水面的花', 
                       '漂浮的樱花', '环绕樱花', '五颜六色的花瓣飞舞', '柳絮', '飘在空中的棉絮', 
                       '树叶', '银杏叶', '枫叶', '落叶', '风中叶', '散落的叶子', '虫子(实际上蝴蝶)', 
                       '蝴蝶', '发光蝴蝶', '飞翔的蝴蝶', '蜜蜂', '蜻蜓', '萤火虫', '羽毛', '天空中的鸟和云', 
                       '金鱼', '太阳', '月亮', '月亮', '满月', '弦月', '新月', '红月', '猩红月亮', '蓝月', 
                       '雨', '雷雨', '雷暴', '暴风雨', '暴雨', '大雨', '中雨', '小雨', '雨中', '雨天', '电', '彩虹',
                         '风', '风吹起', '被风扬起', '微风', '飓风', '尘卷风', '龙卷风', '中等风速', '雪', '雪花', '雪花', 
                         '飘着的雪花', '漂亮精细的雪', '雪崩', '被雪覆盖的', '中雪', '小雪', '霜', '冰', '精细的冰', '冰晶', 
                         '云', '积雨云', '随机分布的云', '多云', '多云', '阴天', '雾气', '蒸汽', '潮湿', '水滴', '液体飞溅', 
                         '飞溅的水', '飞溅水花', '滴水', '地平线', '群山地平线', '天空', '渐变天空', '美丽精细的天空', '燃烧的天空', 
                         '天 际线', '夜空', '星空', '星云', '银河', '银河', '超级银河', '星轨', '五彩斑斓的星轨', '流星', '烟花', 
                         '空中烟火', '极光', '黑烟', '硝烟', '火', '火星子', '精致的火焰', '漂亮的火焰', '火焰漩涡', '飞舞的火焰', 
                         '燃烧', '爆裂魔法', '美丽细致的爆炸', '背后的核爆炸', '战争的火焰', '余烬', '熔化', '魔法', '召 唤魔法阵', 
                         '阴阳', '阴阳球', '鬼火', '彩纸屑', '碎纸屑', '飞溅的彩色碎纸', '折纸', '纸鹤', '彩色的折射', '飘浮的玻璃碎片', 
                         '飘浮的丝带', '漂浮的无色晶体', '发光粒子', '气泡', '大五颜六色的泡泡', '万花筒'],
        "race": race_list,
        "propLoop": {
            "start": 2,
            "p": 0.4,
            "d": "，{i}{property:{i}}，{property:{i}}"
        }
    },
    "result": [
        "二次元少女的{name}",
        "，{facestyle}",
        "，穿着{height}",
        "，{haircolor}头发，{hairstyle}",
        {
            "p": 0.01,
            "d": "，发梢向{haircolor:0}渐变"
        },
        {
            "p": 0.01,
            "d": "，有一缕头发是{haircolor:0}的"
        },
        {
            "p": 0.8,
            "d": "，{daimao}"
        },
        "，{breastsize}",
        {
            "，异色瞳,左眼{color:0}，右眼{color:0}": 0.1,
            "，{color}眼睛": 0.9
        },
        "，画面{property:0}，{background:0}",
        {
            "p": 0.01,
            "d": "，多重人格{propLoop}"
        },
        "，有{race}，{job}，"
    ]
}


class Choicer:
    def _compile(self, d):
        t = type(d)
        if t is list:
            r = []
            for x in d:
                if type(x) is str and x.startswith('{') and x.endswith('}'):
                    for y in self.map[x[1:-1]]:
                        r.append(y[0])
                else:
                    r.append(x)
            p = 1.0 / len(r)
            return [(self._compile(x), p) for x in r]
        elif t is str:
            return d
        elif t is dict:
            if 'start' in d:
                return [(self._compile(d['d']), d['p'], d['start'])]
            elif 'p' in d:
                return [(self._compile(d['d']), d['p'])]
            else:
                return [(self._compile(x), d[x]) for x in d]
        else:
            return []
    reg = re.compile('{(.*?)}')

    def _runstr(self, s: str, vals: dict={}) -> str:
        for k in vals:
            s = s.replace(f'{{{k}}}', vals[k])
        for k in self.vals:
            s = s.replace(f'{{{k}}}', self.vals[k])
        
        def repl(match):
            key = match.group(1)
            k = key.split(':')[0]
            if key not in self.m:
                self.m[key] = set()
            
            while True:
                r = self._run(self.map[k])
                if r not in self.m[key]:
                    self.m[key].add(r)
                    return r
        
        return Choicer.reg.sub(repl, s)

    def _run(self, d) -> str:
        t = type(d)
        if t is str:
            return self._runstr(d)
        elif t is list:
            if len(d) == 1 and len(d[0]) == 3: # loop expr
                sb = []
                d = d[0]
                x = d[0]
                i = d[2]

                while True:
                    sb.append(self._runstr(x, {
                        "i": str(i)
                    }))
                    i += 1
                    if self.rand.random() >= d[1]:
                        break
                return ''.join(sb)
            else:
                r = self.rand.random()
                for d2, p in d:
                    if p > r:
                        return self._run(d2)
                    else:
                        r -= p
                return ''
        else:
            return ''

    def __init__(self, config):
        self.rand = random.Random()
        self.date = config['date']
        self.map = {}

        parts = config['parts']
        for name in parts:
            self.map[name] = self._compile(parts[name])
        
        self.result = [self._compile(x) for x in config['result']]

    def _setseed(self, qq):
        self.rand.seed(qq * (int(time.time()/3600/24) if self.date else 1))
    
    def format_msg(self, qq, name):
        self.vals = {
            "name": name
        }
        self._setseed(qq)
        self.m = {}
        return ''.join([self._run(x) for x in self.result])

replace_dict = {
    "ACUP": "flat_chest",
    "BCUP": "small_breasts",
    "CCUP": "medium breasts",
    "DCUP": "huge breasts",
    "ECUP": "large_breast",
    "FCUP": "large_breast",
    "GCUP": "gigantic breasts",
    "惊天巨乳": "gigantic breasts",
    "飞机场": "flat_cheast"
}

@today_girl.handle()
async def _(bot: Bot, event: MessageEvent):
    user_id = str(event.user_id)
    group_id = str(event.group_id)
    get_info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
    random_int_str = str(random.randint(0, 65535))
    user_name = get_info["nickname"] + random_int_str
    user_id_random = user_id + random_int_str
    inst = Choicer(data_dict)
    msg = inst.format_msg(user_id_random, user_name)
    to_user = msg.replace(random_int_str, "")

    try:
        await bot.send(event=event, 
                        message=f"锵锵~~~{to_user}正在为你生成二次元图像捏~随机种子是{random_int_str}")
    except ActionFailed:
        await bot.send(event=event, 
                        message=f"风控了...不过图图我还是会画给你的...")
        
    # 简单粗暴的替换
    for i in data_dict["parts"]["breastsize"]:
        if i in msg:
            to_ai = msg.replace(i, replace_dict[f"{i}"])
    for i in data_dict["parts"]["hairstyle"]:
        if i in to_ai:
            to_ai = to_ai.replace(i, hairstyle_dict[f"{i}"])
            break
    for i in data_dict["parts"]["daimao"]:
        if i in to_ai:
            to_ai = to_ai.replace(i, pose_dict[f"{i}"])
            break

    try:
        to_ai = to_ai.replace(f"二次元少女的{user_name}", "")
        logger.debug(to_ai)
        tags = await translate(to_ai, "en")
    except:
        await today_girl.finish("翻译API出错辣")
    else:
        tags = basetag + tags
        ntags = lowQuality
        fifo = AIDRAW(user_id=user_id, 
                      group_id=group_id, 
                      tags=tags, 
                      ntags=ntags)
        try:
            await fifo.post()
        except Exception as e:
            await today_girl.finish(f"服务端出错辣,{e.args}")
        else:
            img_msg = MessageSegment.image(fifo.result[0])
            try:
                await bot.send(event=event, 
                            message=f"这是你的二次元形象,hso\nprompts:{tags}" +img_msg+ f"生成耗费时间{fifo.spend_time}s", 
                            at_sender=True, reply_message=True)
            except ActionFailed:
                await bot.send(event=event, 
                            message=img_msg, 
                            at_sender=True, reply_message=True)
