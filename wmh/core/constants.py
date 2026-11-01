"""与原程序逐字对应的文案、常量与元数据。

来源：反编译 inner_src/-1hHVP.readable.cs（主窗体 InitializeComponent 与事件处理）
以及 Properties/AssemblyInfo.cs。界面模块只从这里取文案，不再散落字符串。
"""

from dataclasses import dataclass

APP_TITLE = "隐形水印工具 V1.2---吾爱破解论坛首发"
PY_TITLE = "隐形水印工具 V1.2 (Python 复刻版)"

# Properties/AssemblyInfo.cs
PRODUCT_NAME = "WaterMarkH"
VERSION_TEXT = "版本 1.2.0.0"
COPYRIGHT_TEXT = "Copyright ©  2018"
COMPANY_TEXT = "gozb@163.com"

TAB_ADD = "添加水印"
TAB_GET = "提取水印"

GROUP_OPTIONS = "选项"
GROUP_INFO = "信息"
MENU_TOOLS = "工具"
MENU_HELP = "帮助"
MENU_OPTIONS = "其它选项"
MENU_ABOUT = "关于"

LBL_ADD_IN = "待添加图片："
LBL_ADD_OUT = "保存目录："
LBL_ADD_TEXT = "水印文字："
LBL_ADD_CASE = "转换方案："
LBL_ADD_SCALE = "水印强度："
LBL_PREVIEW = "预览"
LBL_GET_IN = "水印图片："
LBL_GET_CASE = "转换方案："
LBL_GET_SCALE = "图像亮度："

BTN_BROWSE = "浏览"
BTN_FONT = "字体"
BTN_ADD = "添加水印"
BTN_GET = "提取水印"
BTN_OK = "确定"
BTN_CANCEL = "取消"
ABOUT_OK = "确定(&O)"

DLG_OPTIONS = "其它选项"
DLG_ABOUT = "关于"
DLG_FONT = "字体"
DLG_TAB_GENERAL = "常规"
DLG_OUT_FORMAT = "输出格式："
OPT_OUT_JPEG = "JPEG"
OPT_OUT_PNG = "PNG"
OPT_OUT_BMP = "BMP"
OPT_OUT_FORMATS = (OPT_OUT_JPEG, OPT_OUT_PNG, OPT_OUT_BMP)

ABOUT_PRODUCT = "产品名称"
ABOUT_VERSION = "版本"
ABOUT_COPYRIGHT = "版权"
ABOUT_COMPANY = "公司名称"

# 校验提示（原程序 MessageBox.Show(..., "提示", MessageBoxIcon.Asterisk)）
TITLE_HINT = "提示"
TITLE_ERROR = "错误"
MSG_NO_ADD_IMAGE = "请选择需要添加水印的图片文件。"
MSG_NO_TEXT = "请输入水印文字。"
MSG_NO_GET_IMAGE = "请选择需要提取水印的图片文件。"

# 状态栏文本
STATUS_READY = "就绪"
STATUS_BUSY_ADD = "正在添加"
STATUS_BUSY_GET = "正在提取"
STATUS_PREVIEW = "生成预览"
STATUS_ADD_OK = "添加成功"
STATUS_ADD_FAIL = "添加失败"
STATUS_GET_OK = "提取成功"
STATUS_GET_FAIL = "提取失败"

FILE_DIALOG_TITLE = "打开图片"
FILE_DIALOG_FILTER = "图像文件(*.BMP;*.JPG;*.GIF;*.PNG)|*.BMP;*.JPG;*.GIF;*.PNG|所有文件(*.*)|*.*"
FOLDER_DIALOG_TITLE = "选择保存的目录"

OUTPUT_SUFFIX = "_WaterMark"

FILE_OPEN_PATTERNS = (
    ("图像文件", ("*.bmp", "*.jpg", "*.jpeg", "*.gif", "*.png")),
    ("所有文件", ("*.*",)),
)


@dataclass(frozen=True)
class SchemeInfo:
    """一个“转换方案”：编号、名称与界面提示。"""

    index: int
    name: str
    add_hint: str
    get_hint: str

    @property
    def add_text(self) -> str:
        return f"{self.name}：{self.add_hint}"

    @property
    def get_text(self) -> str:
        return f"{self.name}：{self.get_hint}"


SCHEME_ITEMS = ("方案一", "方案二", "方案三", "方案四", "方案五")

_SCHEME_HINTS = (
    "效果最佳，输出的图片比例可能会变化。",
    "高质量缩放，输出的图片比例不变，适用大图。",
    "低质量缩放，输出的图片比例不变，适用小图。",
    "固定像素填充，输出的图片比例不变。",
    "部分区域添加，输出的图片比例不变。",
)

SCHEMES = tuple(
    SchemeInfo(i, name, hint, "匹配输出时选择的方案。")
    for i, (name, hint) in enumerate(zip(SCHEME_ITEMS, _SCHEME_HINTS))
)

# 悬停提示（原程序 toolTip.SetToolTip 的三段说明）
TIP_ADD_SCALE = (
    "水印强度：如果添加水印后效果不好，可以尝试增加强度，"
    "但图片干扰会随之增加。"
)
TIP_GET_SCALE = "图像亮度：设置提取水印时图像的显示亮度。"
TIP_ADD_TEXT = "水印文字：设置添加的水印内容，可以根据需要调整字体和大小。"

# NumericUpDown 的范围（原程序 Maximum=1000, Value=50）
SPIN_MIN = 0
SPIN_MAX = 1000
SPIN_DEFAULT = 50

# 水印强度 / 图像亮度的换算系数，来自反编译：
#   float num2 = (float)numericUpDown_1.Value / 500f;   // 添加
#   float num2 = (float)numericUpDown_2.Value / 5f;     // 提取
STRENGTH_DIVISOR = 500.0
BRIGHTNESS_DIVISOR = 5.0

# 原程序 FontDialog 默认字体：new Font("黑体", 9.75f, Point)
DEFAULT_FONT_FAMILY = "黑体"
DEFAULT_FONT_POINT = 9.75
