from typing import List
import re

from unidecode import unidecode

from automated_moderation.feature.constants import ORGANISATIONS


# Temporary:
def basic_conversion(text: str) -> str:
    text = unidecode(text)
    return text


# method 1
def split_by_whitespace(text: str) -> List[str]:
    token_list = text.split()
    token_list = [token for token in token_list if token != ""]
    return token_list


# method 2
def remove_non_alphanumeric_split_by_whitespace(text: str) -> List[str]:
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    token_list = text.split()
    token_list = [token for token in token_list if token != ""]
    return token_list


# method 3
def split_by_non_alphanumeric_and_whitespace(text: str) -> List[str]:
    token_list = re.split(r"[^a-zA-Z0-9]", text)
    token_list = [token for token in token_list if token != ""]
    return token_list


# method 4
def split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric(text: str) -> List[str]:
    token_list = split_by_non_alphanumeric_and_whitespace(text)
    result = []
    for token in token_list:
        result.extend(re.findall(r"\d+|\D+", token))
    return result


# helper functions of method 5
def generate_pattern(keyword):
    return r"," + r",?".join(keyword) + r","


def generate_replacement(keyword):
    return r"," + keyword + r","


# method 5
def reconstruct_word_from_fragments(text: str) -> List[str]:
    token_list = split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric(text)
    text_to_reconstruct = ",".join(token_list)
    text_to_reconstruct = "," + text_to_reconstruct + ","

    keywords = [o.lower().split("_") for o in ORGANISATIONS]
    keywords = [word for org in keywords for word in org]
    pattern_list = [generate_pattern(keyword) for keyword in keywords]
    replacement_list = [generate_replacement(keyword) for keyword in keywords]

    for pattern, replacement in zip(pattern_list, replacement_list):
        text_to_reconstruct = re.sub(pattern, replacement, text_to_reconstruct)

    token_list_reconstructed = text_to_reconstruct.split(",")
    token_list_reconstructed = [token for token in token_list_reconstructed if token != ""]
    return token_list_reconstructed


if __name__ == "__main__":
    texts = [
        "good celine bag",
        "#celine #bag",
        "perfomanceline",
        "perfomance line",
        "celine123",
        "celine-bag",
        "good c-e-line bag",
        "good ce line bag",
        "good c.e.l.i.n.e bag",
        "good c e l i n e bag",
        "fred force10",
        "fred force 10",
        "celine di or",
        "Louis Vuitton",
        "L.o.u.i.s V.u.i.t.t.o.n",
        "L.o.u.i.s abc V.u.i.t.t.o.n",
        "Céline sangle bucket bag",
        "C-ELINE 2023 刺繡logo條紋撞色抽繩運動短褲",
        "D-io-r high heels shoes,shoes for women,wedding shoes,heels for women,party shoes",
        "FRED フレッド ダイヤモンド(0.73ct E-VS2-VG) デルフィーヌ エンゲージメントリング PT950 日本サイズ約7号  GIA鑑定書 21020110",
        "歐洲潮牌 Gucc*i兔子短TEE 免運✨現貨【220克優質材質】 新款卡通 動漫兔八哥T恤  高品質短T 字母印花短袖30%蝦幣回饋",
    ]

    for text in texts:
        text = basic_conversion(text).lower()
        tokens = reconstruct_word_from_fragments(text)

        print(tokens)
