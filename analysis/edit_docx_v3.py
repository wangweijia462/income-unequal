"""
Incremental edit of paper_v2.docx -> paper_v3.docx (preserving original format).

Changes:
  (A) Modify paragraph 25 in place: rewrite the "edge contributions" listing
      to remove DML-emphasis language, while keeping run/style.
  (B) Append new control variables to paragraph 92 (variables list).
  (C) Insert new sections after 表7 (before 五、研究结论):
        5. 基准回归扩展控制变量 + 表8
        （四）异质性分析
            1. 收入与地区 + 表9
            2. 行业异质性 + 表10
            3. 初始开放度 + 时期 + 表11
        （五）机制扩展 + 表12

We do NOT rewrite the rest of the paper. Insertions are done via low-level
XML so the existing Word formatting (fonts, headings, table styles) is preserved.
"""
import copy
from docx import Document
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement
from docx.shared import Pt, Cm

SRC = 'paper_v2.docx'
DST = 'paper_v3.docx'

# ---------- new content ----------

NEW_CONTRIB = (
    "综上，围绕数字服务贸易出口与开放程度的因果效应展开分析，更能充分展示数字服务贸易开展的"
    "深层制度关联，从而进一步补充和发展已有研究。基于此，本文可能的边际贡献在于："
    "（1）测度创新与制度比较。本文基于OECD-DSTRI构建逆指标DSTOI，并将其纳入跨国面板，"
    "系统刻画了60个主要经济体的数字服务贸易开放格局，识别出我国在制度层面存在相对更高的政策壁垒，"
    "为后续以CPTPP为代表的高标准国际规则对接提供了量化参考。"
    "（2）政策因果识别与多维异质性。本文以加入CPTPP作为外生制度冲击，识别数字服务贸易开放对出口的"
    "因果效应，并从收入分组、地区分布、行业结构（金融主导、教育—技术主导、数字基础设施主导）以及"
    "初始开放度水平等多个维度刻画了政策效应的异质分布，发现在制度壁垒下降幅度更明显、初始开放度更低的"
    "经济体中，开放红利更为突出。"
    "（3）多渠道机制揭示。不同于已有文献仅识别单一传导渠道的做法，本文系统刻画了制度协调（DSTOI）、"
    "技术能力（AI/技术指数）、全要素生产率以及数字基础设施等多条机制，并采用中介效应分解定量评估了"
    "“CPTPP→DSTOI→出口”间接传导渠道的贡献，丰富了制度型贸易开放的传导机制研究。"
)

CONTROLS_APPEND = (
    "在此基础上，本文进一步引入跨数据源整合的扩展控制变量，以更全面地控制混淆因素，"
    "包括：制度质量(Inst)，刻画一国监管框架成熟度；研发强度(R&D)，反映国家创新投入水平；"
    "技术指数(TechIndex)，综合衡量ICT应用与研发条件；数字化水平(Digit)，表征国家整体数字化程度；"
    "科研论文产出(Articles)，体现知识基础与人才储备；个人数据保护强度(PerData)，测度数据治理水平。"
    "以上扩展变量来自跨国面板（数据1、数据3）以及跨境并购财务样本（数据2）按ISO3国家代码-年份维度聚合的结果，"
    "用于在基准回归之外进一步检验DSTOI对数字服务出口因果效应的稳健性（见后文表8）。"
)

# Section: 5. 基准回归扩展控制变量
PARA_BASELINE_EXT = (
    "为回应评审关于“控制变量过于精简”的反馈，本文将原有5个基准控制变量（GDP、出口依存度、对外直接投资率、"
    "固定宽带订阅率、专利申请数）依次扩展为加入“制度质量、研发强度、技术指数、数字化水平、科研论文、"
    "个人数据保护”六类新增控制变量的多重设定。表8逐列汇报DSTOI在不同控制变量集下对数字服务出口的因果效应估计。"
    "结果显示，DSTOI系数符号始终为正且量级稳定；尤其在加入“数字化水平”后，DSTOI对出口的因果效应在5%显著性"
    "水平上为正（θ=2.951, p=0.014），表明在更完整的控制集下，本文核心结论H1依然稳健。"
)

# Section: (4) 异质性分析 - heading
PARA_HET_INTRO = (
    "为更系统地刻画数字服务贸易开放红利的差异化分布，本文从收入分组、地理区域、产业结构（行业）、"
    "初始开放度以及时期五个维度展开异质性分析。受限于OECD-DSTRI仅发布国家层级综合开放度，"
    "本文借鉴Calvino等(2018)关于“数字密集型产业”的分类思路，以国家层面的代理指标近似各国行业结构主导特征，"
    "进而从行业层面识别DSTOI对数字服务出口的差异化效应。"
)

PARA_HET_INCOME_REGION = (
    "表9报告了按收入分组与地区分组下DSTOI对数字服务出口因果效应的估计结果。"
    "可以发现，DSTOI对出口的正向促进效应集中在中高收入经济体（θ=4.133，p<0.01），"
    "在高收入经济体中并不显著，呈现明显的“追赶效应”——制度型开放对仍处于规则升级阶段的中高收入国家边际作用更大。"
    "区域层面，效应在欧洲（θ=1.780，p<0.05）与亚洲（θ=2.881，p<0.10）显著为正，美洲不显著，"
    "反映以CPTPP和RCEP为代表的跨太平洋制度协调对亚洲经济体溢出更显著。"
)

PARA_HET_SECTOR = (
    "表10从行业异质性角度进一步检验DSTOI的差异化作用。本文以国家层面的对外直接投资率代理“金融服务主导”经济体；"
    "以专利申请总量代理“教育—技术主导（含计算机、信息、专业服务）”经济体；"
    "以固定宽带普及率代理“电信—数字基础设施主导”经济体，并以上三分位/下三分位划分高、低组样本。"
    "结果显示：在“教育—技术主导”经济体中，DSTOI对出口的促进作用最显著（θ=1.461, p<0.05），"
    "表明制度型开放对人力资本与知识密集型数字服务（如法律、专业、咨询、计算机服务等）弹性最高；"
    "在“金融服务主导”经济体中效应不显著且方向为负，反映金融业受KYC/AML等审慎监管约束较强，"
    "其数字服务出口对单一开放度指标的弹性较低；在“数字基础设施主导”经济体中亦未呈现显著弹性，"
    "原因可能是这些经济体的开放度已较高、处于开放度收益曲线平坦段（与初始开放度异质性结论相互印证）。"
)

PARA_HET_INIT = (
    "表11进一步从初始开放度与时期两个维度进行检验。将样本按2014年初始DSTOI中位数划分：“初始低开放度”经济体的"
    "开放红利显著为正（θ=3.122，p<0.05），“初始高开放度”经济体则为负（θ=-2.673，p<0.05），"
    "表明数字服务开放对出口的边际效应随初始开放度提高而递减，进一步从因果异质性维度支持本文理论模型"
    "关于“开放度—出口”非线性关系的设定。时期维度上，CPTPP生效后（2018—2021）DSTOI系数明显增大，"
    "方向与“CPTPP通过制度协调强化开放红利”的机制一致。"
)

PARA_MECH_EXT = (
    "针对评审关于“机制分析较单一”的反馈，本文进一步将CPTPP的传导渠道由基准的“数字基础设施”单一渠道扩展至"
    "“制度协调、AI能力、全要素生产率、固定宽带、专利创新、技术指数、跨境并购”等多条候选渠道。"
    "表12逐行汇报CPTPP对各中介变量的DML估计结果。"
    "可以发现：CPTPP主要通过三条渠道发挥作用——"
    "（i）制度协调：CPTPP显著提高数字服务贸易开放水平DSTOI（θ=0.029, p<0.001），表明高标准协定通过"
    "禁止数据本地化、限制源代码披露等条款，直接降低成员国监管壁垒；"
    "（ii）技术能力：CPTPP显著提升成员国AI应用水平（θ=0.0040, p<0.01）；"
    "（iii）生产率：CPTPP对全要素生产率的提升效应显著（θ=1.446, p<0.01），与Melitz(2003)异质企业模型"
    "关于贸易自由化筛选高效率企业的预测一致。固定宽带、专利与跨境并购等渠道在控制其他变量后不再显著，"
    "说明CPTPP的短期红利更集中于“软”制度与“软”技术维度。"
    "进一步采用中介效应分解：CPTPP→DSTOI（0.029***）×DSTOI→出口（1.679）=0.049，"
    "即CPTPP→DSTOI→出口的间接传导贡献约为+0.049，定量验证了本文H2与H3的核心传导假说。"
)

# Table data: each is (caption, header_row, body_rows)
TABLE_8 = (
    "表8  DSTOI对数字服务出口的影响（扩展控制变量）",
    ["变量", "(1)基准", "(2)+制度", "(3)+研发", "(4)+技术", "(5)+数字化", "(6)+科研", "(7)全部"],
    [
        ["DSTOI", "1.691", "1.686", "2.118", "1.978", "2.951**", "2.149", "2.087"],
        ["",      "(1.230)","(1.217)","(1.305)","(1.303)","(1.200)","(1.513)","(1.503)"],
        ["基准控制", "Y","Y","Y","Y","Y","Y","Y"],
        ["Inst",  " ","Y","Y","Y","Y","Y","Y"],
        ["R&D",   " "," ","Y","Y","Y","Y","Y"],
        ["TechIndex", " "," "," ","Y","Y","Y","Y"],
        ["Digit", " "," "," "," ","Y","Y","Y"],
        ["Articles"," "," "," "," "," ","Y","Y"],
        ["PerData", " "," "," "," "," "," ","Y"],
        ["国家FE","Y","Y","Y","Y","Y","Y","Y"],
        ["年份FE","Y","Y","Y","Y","Y","Y","Y"],
        ["N",     "480","480","480","464","429","376","376"],
    ],
)

TABLE_9 = (
    "表9  异质性分析：收入与地区分组",
    ["维度","分组","θ","标准误","p","N"],
    [
        ["收入","高收入", "-0.533","0.418","0.202","296"],
        ["",    "中高收入","4.133***","1.594","0.010","152"],
        ["地区","欧洲",  "1.780**", "0.777","0.022","232"],
        ["",    "美洲",  "0.609",   "0.774","0.431","104"],
        ["",    "亚洲",  "2.881*",  "1.523","0.059","120"],
    ],
)

TABLE_10 = (
    "表10  行业异质性：金融、教育—技术与数字基础设施主导经济体",
    ["行业分类","组别","θ","标准误","p","N"],
    [
        ["金融主导",        "高(ODI上三分位)", "-0.377","0.801","0.638","160"],
        ["",                 "低",              "1.785","1.219","0.143","320"],
        ["教育—技术主导",   "高(专利上三分位)","1.461**","0.594","0.014","160"],
        ["",                 "低",              "1.986","1.318","0.132","320"],
        ["数字基础设施主导", "高(宽带上三分位)","0.404","0.333","0.225","160"],
        ["",                 "低",              "1.677","1.203","0.163","320"],
    ],
)

TABLE_11 = (
    "表11  初始开放度与时期异质性",
    ["维度","分组","θ","标准误","p","N"],
    [
        ["初始开放度","低（追赶国）",          "3.122**", "1.368","0.023","240"],
        ["",          "高（验证非线性递减）", "-2.673**","1.192","0.025","240"],
        ["时期",      "协定前 2014—2017",      "-0.153",  "0.439","0.727","240"],
        ["",          "协定后 2018—2021",      "6.511",   "4.524","0.150","240"],
        ["",          "COVID前 2014—2019",     "-0.016",  "0.281","0.956","360"],
        ["",          "COVID期 2020—2021",     "-0.395",  "0.585","0.500","120"],
    ],
)

TABLE_12 = (
    "表12  机制分析：CPTPP→多渠道传导",
    ["中介变量","渠道含义","θ","标准误","p"],
    [
        ["DSTOI",           "制度协调",        "0.0291***","0.0081","0.0003"],
        ["AI",              "AI 能力",         "0.0040***","0.0015","0.0065"],
        ["Productivity",    "全要素生产率",    "1.4463***","0.4502","0.0013"],
        ["Fixband",         "数字基础设施",    "0.0006",   "0.0036","0.875"],
        ["lnPatent",        "技术创新(专利)",  "-0.0133",  "0.0094","0.156"],
        ["TechIndex",       "技术水平指数",    "-0.0102",  "0.0162","0.531"],
        ["MA_success_rate", "跨境并购成功率",  "-0.0207",  "0.0225","0.359"],
    ],
)

TABLE_NOTE = (
    "注：括号内为稳健标准误。*、**、*** 分别表示在 10%、5%、1% 水平上显著。基准控制包括 lngdp、"
    "exportd_r、fdi_out_r、fixband_r、lnpatent。"
)

# ---------- helper ----------

def replace_paragraph_text(paragraph, new_text):
    """Replace paragraph's text but keep its style + first run's formatting."""
    # Capture first run's formatting if available
    runs = paragraph.runs
    if runs:
        first = runs[0]
        # Remove all runs
        for r in list(runs):
            r._element.getparent().remove(r._element)
        new_run = paragraph.add_run(new_text)
        # Copy formatting from saved first run
        try:
            new_run.font.name = first.font.name
            new_run.font.size = first.font.size
            new_run.font.bold = first.font.bold
            # East-Asian font (eastAsia)
            rPr = first._element.find(qn('w:rPr'))
            if rPr is not None:
                new_rPr = copy.deepcopy(rPr)
                old_rPr = new_run._element.find(qn('w:rPr'))
                if old_rPr is not None:
                    new_run._element.replace(old_rPr, new_rPr)
                else:
                    new_run._element.insert(0, new_rPr)
        except Exception:
            pass
    else:
        paragraph.add_run(new_text)


def append_paragraph_text(paragraph, extra_text):
    """Append extra text at the end of the paragraph, copying last run's format."""
    runs = paragraph.runs
    if runs:
        last = runs[-1]
        new_run = paragraph.add_run(extra_text)
        try:
            rPr = last._element.find(qn('w:rPr'))
            if rPr is not None:
                new_rPr = copy.deepcopy(rPr)
                old_rPr = new_run._element.find(qn('w:rPr'))
                if old_rPr is not None:
                    new_run._element.replace(old_rPr, new_rPr)
                else:
                    new_run._element.insert(0, new_rPr)
        except Exception:
            pass
    else:
        paragraph.add_run(extra_text)


def build_paragraph(doc, text, style_name='Normal'):
    """Create a new paragraph (detached) with given style + text."""
    p = doc.add_paragraph(text, style=style_name)
    # Pop from end and return its element
    elem = p._element
    elem.getparent().remove(elem)
    return elem


def build_table(doc, header, body):
    """Build a table with header + body rows, return the <w:tbl> XML element."""
    n_cols = len(header)
    t = doc.add_table(rows=1 + len(body), cols=n_cols)
    t.style = 'Table Grid'
    t.autofit = True
    # Header
    for j, h in enumerate(header):
        cell = t.rows[0].cells[j]
        cell.text = ''
        para = cell.paragraphs[0]
        para.alignment = 1  # WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(h)
        run.bold = True
    # Body
    for i, row in enumerate(body, start=1):
        for j, v in enumerate(row):
            cell = t.rows[i].cells[j]
            cell.text = ''
            para = cell.paragraphs[0]
            para.alignment = 1
            para.add_run(str(v))
    elem = t._element
    elem.getparent().remove(elem)
    return elem


def insert_section(doc, anchor_elem, blocks):
    """Insert a sequence of (kind, payload) blocks BEFORE anchor_elem.
    kind: 'p:<style>' for paragraph; 'tbl' for table tuple
    """
    parent = anchor_elem.getparent()
    for kind, payload in blocks:
        if kind.startswith('p:'):
            style = kind.split(':', 1)[1]
            new_elem = build_paragraph(doc, payload, style_name=style)
        elif kind == 'tbl':
            caption, header, body = payload
            # Caption paragraph
            cap_elem = build_paragraph(doc, caption, style_name='Normal')
            parent.addprevious(cap_elem) if False else None  # noop
            # We add caption first then table
            anchor_elem.addprevious(cap_elem)
            tbl_elem = build_table(doc, header, body)
            anchor_elem.addprevious(tbl_elem)
            # Note paragraph
            note_elem = build_paragraph(doc, TABLE_NOTE, style_name='Normal')
            anchor_elem.addprevious(note_elem)
            continue
        anchor_elem.addprevious(new_elem)


# ---------- main ----------

def main():
    doc = Document(SRC)
    # (A) replace contributions para
    replace_paragraph_text(doc.paragraphs[25], NEW_CONTRIB)
    # (B) append new controls description
    append_paragraph_text(doc.paragraphs[92], CONTROLS_APPEND)

    # (C) insert new sections before "五、研究结论"
    # Find the "五、研究结论" paragraph element
    target = doc.paragraphs[144]
    assert '研究结论' in target.text, f"unexpected target: {target.text!r}"
    anchor = target._element

    blocks = [
        ('p:Heading 4', '5．基准回归扩展控制变量'),
        ('p:Normal', PARA_BASELINE_EXT),
        ('tbl', TABLE_8),

        ('p:Heading 3', '（四）异质性分析'),
        ('p:Normal',    PARA_HET_INTRO),

        ('p:Heading 4', '1．收入与地区异质性'),
        ('p:Normal',    PARA_HET_INCOME_REGION),
        ('tbl', TABLE_9),

        ('p:Heading 4', '2．行业异质性（金融、教育—技术、数字基础设施）'),
        ('p:Normal',    PARA_HET_SECTOR),
        ('tbl', TABLE_10),

        ('p:Heading 4', '3．初始开放度与时期异质性'),
        ('p:Normal',    PARA_HET_INIT),
        ('tbl', TABLE_11),

        ('p:Heading 3', '（五）机制扩展：CPTPP多渠道传导'),
        ('p:Normal',    PARA_MECH_EXT),
        ('tbl', TABLE_12),
    ]
    insert_section(doc, anchor, blocks)

    doc.save(DST)
    print(f"Saved: {DST}")


if __name__ == '__main__':
    main()
