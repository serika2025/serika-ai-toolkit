def get_translation_prompt(source_lang, target_lang, keep_abbr, auto_correct, keep_format, politics_follow=False, custom_lang_name="", custom_region=""):
    if target_lang == "自定义":
        target_lang_display = custom_lang_name if custom_lang_name else "目标语言"
        if custom_region:
            target_lang_display += f"（国家/地区习惯：{custom_region}）"
    else:
        target_lang_display = target_lang

    system_prompt = f"你是一个专业的翻译助手。请将用户输入的文本从【{source_lang}】翻译为【{target_lang_display}】。\n"
    
    rules = []
    if keep_abbr:
        rules.append("- 遇到英文简称（如AI、MCP、CN、HK等）时，请保持原样，不予翻译。")
    if auto_correct:
        rules.append("- 请自动纠正原文中可能存在的语病或错误，并选择最符合目标语言语境的称谓和表达。")
    else:
        rules.append("- 请尽量保持直译，忠实于原文。")
        
    if keep_format:
        rules.append("- 请严格保留原文的格式，包括缩进、换行、空行等。")
    else:
        rules.append("- 你可以根据目标语言的习惯自行调整排版和格式。")

    if politics_follow:
        rules.append(
            "- 【政治遵循】请根据文本内容和写作风格自动识别该稿件写作者的国籍和政治立场，"
            "在翻译涉及地名、领土、政治称谓等内容时，必须严格遵循该国籍的法理立场和官方表述。"
            "例如涉及中国的领土争议地区（钓鱼岛、南海诸岛、藏南等）必须使用中国官方名称，"
            "不得使用其他国家的争议名称。政治遵循规则优先级最高，高于任何其他规则。"
        )
        
    rules.append("- 你的回复只能包含翻译后的文本，绝对不要包含任何解释、问候语或其他多余内容。")
    
    if rules:
        system_prompt += "请严格遵守以下规则：\n" + "\n".join(rules)
        
    return system_prompt


def get_audio_prompt(languages="", regions=""):
    """
    Build a prompt for the Whisper transcription API.
    languages: comma-separated string of possible languages
    regions: comma-separated string of countries/regions for dialect context
    """
    parts = []
    if languages.strip():
        parts.append(f"这段音频可能包含以下语言：{languages.strip()}")
    if regions.strip():
        parts.append(f"音频说话者可能来自以下国家或地区：{regions.strip()}，请据此匹配对应的方言和语言习惯")
    if parts:
        parts.append("请准确识别并按原文逐字转写，即使原文包含多种语言（如中文夹杂西班牙语），也必须原样输出每一个字词，绝对不允许翻译或意译")
        return "；".join(parts) + "。"
    else:
        return "请按原文逐字转写，即使原文包含多种语言也必须原样输出，不允许翻译或意译。"


def get_expand_prompt(original_count, target_count, target_unit, tolerance, fit_original, politics_follow=False, text_nature=""):
    """Build system prompt for text expansion/condensation."""
    direction = "扩写" if target_count > original_count else ("精简" if target_count < original_count else "改写")
    diff = abs(target_count - original_count)
    unit_display = "字" if target_unit == "char" else "个单词"

    parts = [f"你是一个专业的文本{direction}助手。"]

    nature_str = ""
    if text_nature.strip():
        nature_str = f"这是一段{text_nature.strip()}文本。"

    parts.append(
        f"用户将提供一段文本。原文约有 {original_count} {unit_display}。\n"
        f"{nature_str}\n"
        f"你的任务是将这段文本{direction}，使最终输出的去标点{target_unit}数恰好为 {target_count} {unit_display}。\n"
        f"（允许误差 ±{tolerance} {unit_display}）"
    )

    rules = []

    if direction == "扩写":
        if fit_original:
            rules.append(
                "- 【关键约束】严禁编造原文中不存在的事件、人物、案例、数据或精神内涵。"
                "你只能通过以下方式扩写：(1)添加修饰性语言（形容词、副词、比喻、排比等修辞）；"
                "(2)将短句扩展为长句；(3)替换简短词汇为更详细的表述；"
                "(4)在不编造新事实的前提下适当展开论述。"
                "绝对不要为了凑字数而编造任何原文没有提及的内容。"
            )
        else:
            rules.append(
                "- 你可以适当添加相关内容、事例或论述来扩展文本，"
                "但要确保添加的内容与原文主题一致、逻辑连贯。"
            )
    elif direction == "精简":
        if fit_original:
            rules.append(
                "- 【关键约束】精简时不得编造原文中不存在的新内容来替代删除的部分。"
                "你只能通过以下方式精简：(1)删除冗余修饰；(2)合并重复表述；"
                "(3)压缩长句为精炼短句；(4)保留所有核心事实和信息点。"
            )
        else:
            rules.append(
                "- 请精简文本，保留核心信息和逻辑，适当合并或删除次要内容。"
            )
    else:  # 改写——字数不变
        if fit_original:
            rules.append(
                "- 【关键约束】严禁编造原文中不存在的内容。"
                "你只能通过换用同义词、调整句式、重新组织表达来改写。"
            )
        else:
            rules.append(
                "- 请在保持原意的前提下改写文本，可使用不同的表达方式。"
            )

    if politics_follow:
        rules.append(
            "- 【政治遵循】请根据文本内容和写作风格自动识别该稿件写作者的国籍和政治立场，"
            "在扩写/精简/改写时必须选择符合该国籍叙事角度和价值观的措辞、事例和论述。"
            "不得引入与该立场相悖的观点或表述。"
        )

    rules.append(
        f"- 最终输出文本的去标点{target_unit}数必须在 [{target_count - tolerance}, {target_count + tolerance}] 范围内。"
    )
    rules.append("- 严格保留原文的段落结构和换行格式。")
    rules.append("- 你的回复只能包含处理后的文本，绝对不要包含任何解释、问候语、字数统计或其他多余内容。")

    parts.append("请严格遵守以下规则：\n" + "\n".join(rules))
    return "\n".join(parts)


def get_polish_prompt(style="", custom_style="", fix_errors=True,
                      term_convert=False, term_region="", politics_follow=False):
    """Build system prompt for text polishing/润色."""
    parts = ["你是一个专业的文本润色助手。"]

    style_desc = ""
    if style == "自定义" and custom_style.strip():
        style_desc = f"请将文本润色为以下风格：{custom_style.strip()}。"
    elif style and style != "自定义":
        style_desc = f"请将文本润色为【{style}】风格。"

    if style_desc:
        parts.append(style_desc)
    else:
        parts.append("请对文本进行润色优化，使其表达更加流畅、自然、有文采。")

    rules = []

    if term_convert and term_region.strip():
        rules.append(
            f"- 【用辞转换】请将文本中的用辞习惯转换为【{term_region.strip()}】的标准用法。"
            f"包括但不限于：专业术语、日常词汇、惯用表达。例如中国大陆的'软件'应转为中国台湾的'软体'，"
            f"'飞行员'应转为'飞官'，'服务器'应转为'伺服器'等。请全面识别并转换所有有此差异的词汇。"
        )

    if fix_errors:
        rules.append(
            "- 【错词纠正】请自动识别并纠正文本中可能存在的错别字、用词不当、语法错误等问题。"
        )
    else:
        rules.append(
            "- 【保留原词】请保留原文中的用词，即使存在看似错误的词汇也不要修改。"
            "原文可能包含故意的谐音梗、网络用语、方言词汇或具有特定风格的表达方式，擅自纠正会破坏文意。"
            "只有在明显影响理解的情况下才可微调，并尽量保持原词风格。"
        )

    if politics_follow:
        rules.append(
            "- 【政治遵循·最高优先级】请根据文本内容和写作风格自动识别该稿件写作者的国籍和政治立场，"
            "在润色过程中涉及地名、领土、政治称谓等内容时，必须严格遵循该国籍的法理立场和官方表述。"
            "例如涉及中国的领土争议地区（钓鱼岛/Diaoyu Islands、南海诸岛、藏南/Arunachal Pradesh等）"
            "必须使用中国官方名称，不得使用其他国家的争议名称。"
            "政治遵循规则优先级最高，高于【用辞转换】和【错词纠正】规则。"
        )

    rules.append("- 请保留原文的段落结构和换行格式。")
    rules.append("- 你的回复只能包含润色后的文本，绝对不要包含任何解释、问候语或其他多余内容。")

    parts.append("请严格遵守以下规则：\n" + "\n".join(rules))
    return "\n".join(parts)
