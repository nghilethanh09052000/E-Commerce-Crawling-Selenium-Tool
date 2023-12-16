from typing import List

from deep_translator import GoogleTranslator
from deep_translator.exceptions import NotValidLength
import langdetect
from langdetect.lang_detect_exception import LangDetectException

from automated_moderation.dataset import BasePost
from app import logger, sentry_sdk


MAX_TRANSLATION_RETRIES = 3


def break_text_in_2(text):
    """
    Break text in 2 taking into account punctuations and spaces.
    """
    half_split = int(len(text) / 2)

    first_half = text[:half_split]
    second_half = text[half_split:]

    # try split by end of sentence punctuation
    second_half_split = [
        second_half.find(p)
        for p in ["\n", "!", ".", "*", ")", ";", "?", "]", "}", "-", "_"]
        if second_half.find(p) >= 0
    ]
    second_half_split = min(second_half_split) if len(second_half_split) > 0 else -1
    if not (second_half_split == -1 or second_half_split > len(second_half) - 2):
        first_half = first_half + second_half[: second_half_split + 1]
        second_half = second_half[second_half_split + 1 :]

        return first_half, second_half

    # try split by space
    second_half_split = second_half.find(" ")
    if not (second_half_split == -1 or second_half_split > len(second_half) - 2):
        first_half = first_half + second_half[: second_half_split + 1]
        second_half = second_half[second_half_split + 1 :]

        return first_half, second_half

    # else return original first and second half
    return first_half, second_half


def break_text_with_limit(text, limit=1000):
    """
    If text too long, break text into multiple part keeping structure.
    """
    texts = [text]
    while any([len(t) > limit for t in texts]):
        new_texts = []
        for t in texts:
            if len(t) > limit:
                t_1, t_2 = break_text_in_2(t)
                new_texts.append(t_1)
                new_texts.append(t_2)
            else:
                new_texts.append(t)

        texts = new_texts
    return texts


def translate_text_into_english(text, retries=0, limit=1000):

    translated_text = None

    if text:
        try:
            texts = break_text_with_limit(text=text, limit=limit)
            translated_text = "".join([GoogleTranslator(source="auto", target="en").translate(t) for t in texts])
        except NotValidLength:
            return text

        except Exception as e:
            if retries < MAX_TRANSLATION_RETRIES:
                return translate_text_into_english(text, retries=retries + 1)

            sentry_sdk.capture_exception(e)

    return translated_text


def get_text_language(text):
    source = None
    try:
        # detect all non 'en' sources
        sources = [l.lang for l in langdetect.detect_langs(text) if (l.lang != "en" and l.prob >= 0.5)]
        source = sources[0] if len(sources) > 0 else None
    except LangDetectException as ex:
        print(ex)
        pass
    except Exception as ex:
        print(ex)
        sentry_sdk.capture_exception(ex)

    return source


def translate_posts(light_posts: List[BasePost]):
    """Translate the description of each post into English if it is not already in English"""

    for post in light_posts:
        try:
            translated_title, translated_desc, source_language = translate_post_text(
                post.title or "", post.description or ""
            )
        except Exception as e:
            logger.error(f"Error translating post text: {e}")
            sentry_sdk.capture_exception(e)
            translated_title, translated_desc, source_language = "", "", None

        post.translated_title = translated_title
        post.translated_description = translated_desc
        post.source_language = source_language
        post.set_text_features()


def translate_post_text(title: str, description: str):
    """Translate text if required"""
    translated_title = translate_text_into_english(title)
    translated_description = translate_text_into_english(description)
    source_language = get_text_language(f"{title} {description}")

    return translated_title, translated_description, source_language
