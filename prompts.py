"""System prompt builders for Elliott Wave content generation."""

DIMENSIONS = [
    "PAIN",
    "MYTH",
    "REFRAME",
    "APPLIED",
    "COMPARE",
    "ANALOGY",
    "CHECKLIST",
    "CASE STUDY",
    "BEGINNER BRIDGE",
    "ADVANCED CHALLENGE",
    "FRUSTRATION",
    "IDENTITY",
]

DIMENSION_DEFINITIONS = {
    "PAIN": (
        "เนื้อหาที่สะท้อนความเจ็บปวดหรือปัญหาที่นักลงทุนเจอจริง "
        "เปิดด้วยความรู้สึกที่คนอ่านรู้สึกว่า 'นั่นแหละฉัน' "
        "แล้วค่อยนำไปสู่แนวคิด Elliott Wave ที่ช่วยแก้ปัญหานั้น"
    ),
    "MYTH": (
        "เนื้อหาที่หักล้างความเชื่อผิดๆ หรือ misconception ที่พบบ่อย "
        "เกี่ยวกับ Elliott Wave หรือการวิเคราะห์กราฟ "
        "เริ่มด้วยความเชื่อที่คนส่วนใหญ่มี แล้วเปิดเผยความจริง"
    ),
    "REFRAME": (
        "เนื้อหาที่เปลี่ยนมุมมองใหม่ให้กับแนวคิดที่รู้จักอยู่แล้ว "
        "ทำให้คนอ่านมองสิ่งเดิมในแง่มุมที่ต่างออกไป "
        "นำไปสู่ความเข้าใจที่ลึกขึ้น"
    ),
    "APPLIED": (
        "เนื้อหาที่แสดงการประยุกต์ใช้ Elliott Wave ในสถานการณ์จริง "
        "เน้นขั้นตอนปฏิบัติที่คนอ่านสามารถนำไปใช้ได้ทันที"
    ),
    "COMPARE": (
        "เนื้อหาที่เปรียบเทียบ Elliott Wave กับเครื่องมือหรือแนวคิดอื่น "
        "ชี้ให้เห็นข้อดีข้อเสีย และบริบทที่เหมาะสมสำหรับแต่ละอย่าง"
    ),
    "ANALOGY": (
        "เนื้อหาที่ใช้การเปรียบเปรยหรืออุปมาอุปมัยจากชีวิตประจำวัน "
        "เพื่ออธิบายแนวคิด Elliott Wave ที่ซับซ้อน ให้เข้าใจง่ายขึ้น"
    ),
    "CHECKLIST": (
        "เนื้อหาในรูปแบบรายการตรวจสอบ ขั้นตอน หรือเกณฑ์ที่ชัดเจน "
        "ช่วยให้คนอ่านมีกรอบในการวิเคราะห์หรือตัดสินใจ"
    ),
    "CASE STUDY": (
        "เนื้อหาที่วิเคราะห์กรณีศึกษาจริงหรือสมมติ "
        "แสดงให้เห็นว่า Elliott Wave ทำงานอย่างไรในบริบทนั้นๆ "
        "เน้นบทเรียนที่ได้"
    ),
    "BEGINNER BRIDGE": (
        "เนื้อหาที่เชื่อมโยงแนวคิดพื้นฐานไปสู่ระดับกลาง "
        "เขียนสำหรับคนที่รู้ Elliott Wave บ้างแล้ว แต่ยังไม่ลึกพอ "
        "ใช้ภาษาเรียบง่าย ไม่ซับซ้อน"
    ),
    "ADVANCED CHALLENGE": (
        "เนื้อหาที่ท้าทายความเข้าใจระดับสูง "
        "สำหรับนักวิเคราะห์ที่มีประสบการณ์ "
        "เจาะลึกรายละเอียดหรือ edge case ที่คนส่วนใหญ่มองข้าม"
    ),
    "FRUSTRATION": (
        "เนื้อหาที่รับรู้และตอบสนองต่อความหงุดหน่ายของนักเรียน "
        "ที่เจอกับ Elliott Wave แสดงความเห็นอกเห็นใจ "
        "แล้วให้ perspective ใหม่หรือวิธีแก้ไข"
    ),
    "IDENTITY": (
        "เนื้อหาที่สร้างหรือเสริมสร้างอัตลักษณ์ของนักวิเคราะห์ Elliott Wave "
        "ทำให้คนอ่านรู้สึกเป็นส่วนหนึ่งของกลุ่มคนที่ 'เข้าใจตลาดจริงๆ'"
    ),
}


def _format_list(items: list) -> str:
    return "\n".join(f"- {i}" for i in items) if items else ""


# ---------------------------------------------------------------------------
# Step 1 — Generate 5 outlines
# ---------------------------------------------------------------------------

def build_outlines_system_prompt(dimension: str, chunk_data: dict) -> str:
    dimension_def = DIMENSION_DEFINITIONS.get(dimension, "")
    chunk_title = chunk_data.get("title", "")
    chunk_summary = chunk_data.get("summary", "")
    chunk_content = chunk_data.get("content", "")
    key_concepts = chunk_data.get("key_concepts", [])
    key_concepts_str = _format_list(key_concepts)

    return f"""คุณคือ Pitch นักการศึกษา Elliott Wave จาก EWR (Elliott Wave Revolution)

## ความรู้ที่ต้องใช้
หัวข้อ: {chunk_title}
สรุป: {chunk_summary}

เนื้อหา:
{chunk_content}

{"แนวคิดสำคัญ:" + chr(10) + key_concepts_str if key_concepts_str else ""}

## Dimension: {dimension}
{dimension_def}

## สิ่งที่ต้องสร้าง
สร้าง 5 แนวทางบทความที่แตกต่างกัน แต่ละแนวทางต้องมี:
1. ชื่อบทความ (กระชับ ดึงดูด)
2. แนวคิดหลัก 1 ประโยค
3. โครงร่าง 4-5 หัวข้อย่อย พร้อมคำอธิบายสั้นๆ

## รูปแบบที่ต้องการ (สำคัญมาก)
คั่นแต่ละแนวทางด้วย ===OUTLINE=== เท่านั้น ห้ามใช้ตัวคั่นอื่น
ตัวอย่าง:
===OUTLINE===
ชื่อ: ...
แนวคิด: ...
โครงร่าง:
- ...
- ...
===OUTLINE===
ชื่อ: ...
...

ห้าม: ใช้ภาษาทางการ, แปลตรงๆจากอังกฤษ, ลงท้ายด้วย "ค่ะ"
ต้อง: เขียนภาษาไทยธรรมชาติ ลงท้ายด้วย "ครับ"
"""


def build_outlines_user_message(dimension: str, chunk_id: str) -> str:
    return (
        f"สร้าง 5 แนวทางบทความ Elliott Wave "
        f"Chunk: {chunk_id} | Dimension: {dimension} ครับ"
    )


# ---------------------------------------------------------------------------
# Step 2 — Generate full article from selected outline
# ---------------------------------------------------------------------------

def _extract_style_rules(style_data: dict) -> str:
    """Extract key voice rules from style.json into a compact instruction block."""
    lines = []

    voice = style_data.get("voice", {})
    if voice.get("self_reference"):
        lines.append(f"- อ้างตัวเองว่า: {', '.join(voice['self_reference'])}")
    if voice.get("reader_reference"):
        lines.append(f"- เรียกผู้อ่านว่า: {', '.join(voice['reader_reference'])}")

    ai_rules = style_data.get("what_ai_must_do", {})
    always = ai_rules.get("always", [])
    never = ai_rules.get("never", [])
    if always:
        lines.append("\nกฎที่ต้องทำเสมอ:")
        lines.extend(f"  ✓ {r}" for r in always)
    if never:
        lines.append("\nกฎที่ห้ามทำ:")
        lines.extend(f"  ✗ {r}" for r in never)

    vocab = style_data.get("vocabulary", {})
    use = vocab.get("phrases_to_use", [])
    avoid = vocab.get("phrases_to_avoid", [])
    if use:
        lines.append(f"\nวลีที่ควรใช้: {', '.join(use[:6])}")
    if avoid:
        lines.append(f"วลีที่ห้ามใช้: {', '.join(avoid)}")

    struct = style_data.get("structure_patterns", {})
    opening = struct.get("opening", {})
    closing = struct.get("closing", {})
    if opening.get("pattern"):
        lines.append(f"\nการเปิดบทความ: {opening['pattern']}")
    if closing.get("signature_close"):
        lines.append(f"การปิดบทความ: {closing['signature_close'][0]}")

    lang = style_data.get("language_patterns", {})
    endings = lang.get("sentence_endings", {})
    if endings.get("most_common"):
        lines.append(f"ลงท้ายประโยค: {', '.join(endings['most_common'])}")
    if lang.get("transitional_whitespace", {}).get("pattern"):
        lines.append("ใช้บรรทัดว่างแบ่ง section เสมอ")

    examples = style_data.get("writing_examples", [])
    if examples:
        lines.append("\n## ตัวอย่างสไตล์การเขียนจริงๆ (เขียนให้ใกล้เคียงแบบนี้)")
        for i, ex in enumerate(examples, 1):
            lines.append(f"\n[ตัวอย่างที่ {i}]\n{ex}")

    return "\n".join(lines)


def build_full_article_system_prompt(
    style_data: dict, chunk_data: dict, dimension: str
) -> str:
    dimension_def = DIMENSION_DEFINITIONS.get(dimension, "")
    chunk_title = chunk_data.get("title", "")
    chunk_content = chunk_data.get("content", "")
    style_rules = _extract_style_rules(style_data)

    return f"""คุณคือ Pitch นักการศึกษา Elliott Wave จาก EWR (Elliott Wave Revolution)

## Voice Guide — ต้องปฏิบัติตามอย่างเคร่งครัด
{style_rules}

## ความรู้พื้นฐาน
หัวข้อ: {chunk_title}
Dimension: {dimension} — {dimension_def}

เนื้อหา:
{chunk_content}

## สิ่งที่ต้องทำ
เขียนบทความเต็มรูปแบบตาม Outline ที่ผู้ใช้ส่งมา
- ความยาว: 400-600 คำ
- รูปแบบ: โพสต์ Facebook/บล็อกภาษาไทย
- น้ำเสียง: เหมือน Pitch กำลังคุยกับเพื่อนแบบ 1:1
- ห้ามใช้ Markdown headers (##) — ใช้ emoji หรือบรรทัดว่างแทน
- ต้องจบด้วยการ invite ให้แสดงความคิดเห็น
"""


def build_full_article_user_message(outline: str) -> str:
    return f"เขียนบทความเต็มรูปแบบตาม Outline นี้ครับ:\n\n{outline}"


# ---------------------------------------------------------------------------
# Legacy helpers (kept for backwards compatibility)
# ---------------------------------------------------------------------------

def build_system_prompt(dimension: str, chunk_data: dict) -> str:
    return build_outlines_system_prompt(dimension, chunk_data)


def build_user_message(dimension: str, chunk_id: str) -> str:
    return build_outlines_user_message(dimension, chunk_id)
