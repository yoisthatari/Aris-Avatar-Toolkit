from __future__ import annotations

import re

DICTIONARY: dict[str, str] = {
    "まばたき": "Blink",
    "笑い": "Blink Happy",
    "ウィンク右": "Wink Right",
    "ウィンク2右": "Wink 2 Right",
    "ウィンク2": "Wink 2",
    "ウィンク": "Wink",
    "ウインク": "Wink",
    "なごみ": "Calm",
    "はぅ": "Close><",
    "びっくり": "Surprised",
    "じと目": "Jito Eye",
    "じと": "Jito",
    "ｷﾘｯ": "Kiri Eye",
    "はちゅ目": "Round Eyes",
    "星目": "Star Eyes",
    "はーと": "Heart Eyes",
    "ハート": "Heart",
    "瞳小": "Small Pupils",
    "瞳大": "Big Pupils",
    "光下": "Highlight Down",
    "恐ろしい子": "Scary",
    "ハイライト消し": "Highlight Off",
    "ハイライト消": "Highlight Off",
    "映り込み消し": "Reflection Off",
    "映り込み消": "Reflection Off",
    "真面目": "Serious",
    "困る": "Worried",
    "にこり": "Cheerful",
    "怒り": "Angry",
    "怒る": "Angry",
    "にやり": "Grin",
    "ニヤリ": "Grin",
    "ぺろっ": "Tongue Out",
    "てへぺろ": "Tehepero",
    "口角上げ": "Mouth Corner Up",
    "口角下げ": "Mouth Corner Down",
    "口横広げ": "Mouth Wide",
    "歯無し上": "No Upper Teeth",
    "歯無し下": "No Lower Teeth",
    "涙": "Tears",
    "頬染め": "Blush",
    "頬": "Cheek",
    "照れ": "Shy",
    "赤面": "Blush",
    "青ざめ": "Pale",
    "がーん": "Shock",
    "汗": "Sweat",
    "悲しむ": "Sad",
    "悲しい": "Sad",
    "驚き": "Surprised",
    "見開き": "Eyes Wide",
    "細目": "Narrow Eyes",
    "上": "Up",
    "下": "Down",
    "あ2": "Ah 2",
    "あ": "Ah",
    "い": "Ch",
    "う": "U",
    "え": "E",
    "お": "Oh",
    "ん": "N",
    "ワ": "Wa",
    "全ての親": "Root",
    "センター": "Center",
    "グルーブ": "Groove",
    "下半身": "Lower Body",
    "上半身2": "Upper Body 2",
    "上半身3": "Upper Body 3",
    "上半身": "Upper Body",
    "首": "Neck",
    "頭": "Head",
    "顔": "Face",
    "肩": "Shoulder",
    "腕捩": "Arm Twist",
    "腕": "Arm",
    "ひじ補助": "Elbow Helper",
    "ひじ": "Elbow",
    "肘": "Elbow",
    "手捩": "Wrist Twist",
    "手首": "Wrist",
    "手": "Hand",
    "親指": "Thumb",
    "人差し指": "Index Finger",
    "人差指": "Index Finger",
    "中指": "Middle Finger",
    "薬指": "Ring Finger",
    "小指": "Little Finger",
    "腰": "Waist",
    "足ＩＫ": "Leg IK",
    "足IK": "Leg IK",
    "足首": "Ankle",
    "足先EX": "Toe EX",
    "つま先ＩＫ": "Toe IK",
    "つま先IK": "Toe IK",
    "つま先": "Toe",
    "ひざ": "Knee",
    "膝": "Knee",
    "足": "Leg",
    "脚": "Leg",
    "両目": "Eyes",
    "目": "Eye",
    "眉": "Eyebrow",
    "まぶた": "Eyelid",
    "まつげ": "Eyelashes",
    "睫毛": "Eyelashes",
    "白目": "Eye White",
    "瞳": "Pupil",
    "舌": "Tongue",
    "歯": "Teeth",
    "口": "Mouth",
    "唇": "Lips",
    "鼻": "Nose",
    "耳": "Ear",
    "髪": "Hair",
    "前髪": "Front Hair",
    "後髪": "Back Hair",
    "横髪": "Side Hair",
    "触角": "Antenna",
    "アホ毛": "Ahoge",
    "ツインテール": "Twintails",
    "ポニーテール": "Ponytail",
    "おさげ": "Braids",
    "胸": "Chest",
    "乳": "Breast",
    "お腹": "Belly",
    "尻": "Butt",
    "尻尾": "Tail",
    "しっぽ": "Tail",
    "羽": "Wing",
    "翼": "Wings",
    "角": "Horn",
    "ネコミミ": "Cat Ears",
    "猫耳": "Cat Ears",
    "左右": "Both",
    "左": "Left ",
    "右": "Right ",
    "前": "Front",
    "後ろ": "Back",
    "後": "Back",
    "横": "Side",
    "先": "Tip",
    "補助": "Helper",
    "捩": "Twist",
    "親": "Parent",
    "子": "Child",
    "その他": "Other",
    "他": "Other",
    "体": "Body",
    "肌": "Skin",
    "服": "Clothes",
    "上着": "Jacket",
    "シャツ": "Shirt",
    "スカート": "Skirt",
    "ズボン": "Pants",
    "パンツ": "Panties",
    "ブラ": "Bra",
    "靴下": "Socks",
    "靴": "Shoes",
    "ブーツ": "Boots",
    "手袋": "Gloves",
    "帽子": "Hat",
    "リボン": "Ribbon",
    "ネクタイ": "Necktie",
    "メガネ": "Glasses",
    "眼鏡": "Glasses",
    "アクセサリー": "Accessory",
    "飾り": "Decoration",
    "ボタン": "Button",
    "袖": "Sleeve",
    "襟": "Collar",
    "フリル": "Frill",
    "ベルト": "Belt",
    "エッジ": "Edge",
    "輪郭": "Outline",
    "表情": "Expression",
    "材質": "Material",
    "メッシュ": "Mesh",
    "モデル": "Model",
    "その1": "Part 1",
    "その2": "Part 2",
    "その3": "Part 3",
}

_KANA_DIGRAPHS: dict[str, str] = {
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
}

_KANA_SINGLE: dict[str, str] = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "wo", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo", "っ": "", "ー": "-",
}

_SORTED_TERMS = sorted(DICTIONARY, key=len, reverse=True)


def _katakana_to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char
        for char in text
    )


def _romanize_kana(text: str) -> str:
    text = _katakana_to_hiragana(text)
    out: list[str] = []
    i = 0
    while i < len(text):
        pair = text[i:i + 2]
        if pair in _KANA_DIGRAPHS:
            out.append(_KANA_DIGRAPHS[pair])
            i += 2
            continue
        char = text[i]
        if char == "っ" and i + 1 < len(text):
            nxt = _romanize_kana(text[i + 1])
            out.append(nxt[0] if nxt and nxt[0].isalpha() else "")
            i += 1
            continue
        out.append(_KANA_SINGLE.get(char, char))
        i += 1
    return "".join(out)


def contains_japanese(text: str) -> bool:
    return bool(re.search(r"[぀-ヿ㐀-䶿一-鿿ｦ-ﾟ]", text))


def translate(text: str) -> str:
    if not contains_japanese(text):
        return text
    result = text
    for term in _SORTED_TERMS:
        if term in result:
            result = result.replace(term, DICTIONARY[term])
    if contains_japanese(result):
        result = _romanize_kana(result)
    result = re.sub(r"\s+", " ", result).strip()
    return result or text
