from typing import List

import pandas as pd

from automated_moderation.feature.constants import INFRINGING_KEYWORDS, ORGANISATIONS
from .text_tokenization import (
    split_by_whitespace,
    remove_non_alphanumeric_split_by_whitespace,
    split_by_non_alphanumeric_and_whitespace,
    split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric,
    reconstruct_word_from_fragments,
    basic_conversion,
)
from . import Feature

# from automated_moderation.model import PredictionRunner


class OrganisationName(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_organisation__name",
            description="Name of the post's organisation",
            default_value="None",
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["organisation.name"]


class LogoDetected(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_image__logo_detected",
            description="Whether the Gucci logo has been detected on at least one image or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(
            lambda images: any(image["logo_detected"] for image in images) if images is not None else None
        )


class Hashtags(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__hashtags",
            description="Hashtags in the post description",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["hashtags"].apply(lambda hashtags: " ".join(hashtags) if hashtags else "")


class HashtagsNumber(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__hashtags_number",
            description="Number of hashtags in the post description",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["description"].str.count("#")


class PostCategory(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_post__category",
            description="Post's product category",
            default_value="None",
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["category.name"]


class InfringingKeywordCount(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__infringing_kw",
            description="Whether the readable descrption contains infring keywords or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["translated_text"].str.count("|".join(INFRINGING_KEYWORDS))


class PostTranslatedText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__translated_text",
            description="The post translated text",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["translated_text"]


class PostOriginalText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__original_text",
            description="The post original text",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["original_text"]


class IsPosterKnown(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account__is_poster_known",
            description="Whether the poster was already in our database or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.name"].notna().astype(int)


class PosterInfringingNumberForOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account_organisation__poster_infringing_number_for_organisation",
            description="Number of infringing posts of this poster for the given organisation",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.total_infringing_posts_for_org"]


class PosterPostNumberForOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account_organisation__poster_post_number_for_organisation",
            description="Number of posts of this poster for the given organisation",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.total_posts_for_org"]


class PosterInfringingPercentForOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account_organisation__poster_infringing_percent_for_organisation",
            description="Percent of infringing posts of this poster for the given organisation",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.total_infringing_posts_for_org"] / posts["poster.total_posts_for_org"]


class PosterInfringingNumberForAllOrganisations(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account__poster_infringing_number_for_all_organisations",
            description="Number of infringing posts of this poster for all organisations",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.total_infringing_posts"]


class PosterInfringingPercentForAllOrganisations(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account__poster_infringing_percent_for_all_organisations",
            description="Percent of infringing posts of this poster for all given organisations",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["poster.total_infringing_posts"] / posts["poster.total_posts"]
            if posts["poster.total_posts"] > 0
            else -1
        )


class PosterPostNumberForAllOrganisations(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account__poster_post_number_for_all_organisations",
            description="Number of posts of this poster for all organisations",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.total_posts"]


class ClusterInfringingNumberForOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_cluster_organisation__cluster_infringing_number_for_organisation",
            description="Number of infringing posts of this post's cluster for the given organisation",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.cluster_total_infringing_posts_for_org"]


class ClusterPostNumberForOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_cluster_organisation__cluster_post_number_for_organisation",
            description="Number of posts of this post's cluster for the given organisation",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.cluster_total_posts_for_org"]


class ClusterInfringingPercentForOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_cluster_organisation__cluster_infringing_percent_for_organisation",
            description="Percent of infringing posts of this post's cluster for the given organisation",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["poster.cluster_total_infringing_posts_for_org"] / posts["poster.cluster_total_posts_for_org"]
            if posts["poster.cluster_total_posts_for_org"] > 0
            else -1
        )


class ClusterInfringingNumberForAllOrganisations(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_cluster__cluster_infringing_number_for_all_organisations",
            description="Number of infringing posts of this post's cluster for all organisations",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.cluster_total_infringing_posts"]


class ClusterInfringingPercentForAllOrganisations(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_cluster__cluster_infringing_percent_for_all_organisations",
            description="Percent of infringing posts of this post's cluster for all organisations",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["poster.cluster_total_infringing_posts"] / posts["poster.cluster_total_posts"]
            if posts["poster.cluster_total_posts"] > 0
            else -1
        )


class ClusterPostNumberForAllOrganisations(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_cluster_organisation__cluster_post_number_for_all_organisations",
            description="Number of posts of this post's cluster for all organisations",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["poster.cluster_total_posts"]


class OrganisationInOriginalText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_original_text",
            description="Whether the organisation is in the post's text or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        # TODO: test
        posts[self.name] = (
            posts["organisation.name"].str.lower().str.replace("_", " ").isin(posts["original_text"].str.lower())
        )
        # posts[self.name] = posts["original_text"].str.lower().str.contains("&".join(posts["organisation.name"].str.lower().str.split("_")))


class OrganisationInTranslatedText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_translated_text",
            description="Whether the organisation is in the post's translated text or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["organisation.name"]
            .str.lower()
            .str.replace("_", " ")
            .isin(posts["translated_text"].str.lower())
            .astype(int)
        )


class NumberOfOrganisationsInOriginalText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_original_text",
            description="Number of organisations in post's text (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        organisations = [o.replace("_", " ").lower() for o in ORGANISATIONS]
        posts[self.name] = posts["original_text"].str.lower().str.count("|".join(organisations))


class NumberOfOrganisationsInTranslatedText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_translated_text",
            description="Number of organisations in post's translated text (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        organisations = [o.replace("_", " ").lower() for o in ORGANISATIONS]
        posts[self.name] = posts["translated_text"].str.lower().str.count("|".join(organisations))


class OrganisationInPosterName(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account_organisation__organisation_in_poster_name",
            description="Whether the organisation is in the poster's name or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["organisation.name"]
            .str.lower()
            .str.replace("_", " ")
            .isin(posts["translated_text"].str.lower())
            .astype(int)
        )


class NumberOfOrganisationsInPosterName(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_account__organisations_number_in_poster_name",
            description="Number of organisations in poster's name (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        organisations = [o.replace("_", " ").lower() for o in ORGANISATIONS]
        posts[self.name] = posts["poster.name"].str.lower().str.count("|".join(organisations))


class OrganisationInHashtags(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_hashtags",
            description="Whether the organisation is in the post's hashtags or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["organisation.name"].str.lower().str.replace("_", " ").isin(posts["hashtags"].astype(str).str.lower())
        )


class NumberOfOrganisationsInHashtags(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_hashtags",
            description="Number of organisations in post's hashtags (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        organisations = [o.replace("_", " ").lower() for o in ORGANISATIONS]
        posts[self.name] = posts["hashtags"].astype(str).str.lower().str.count("|".join(organisations))


class EmailInText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__email_in_post_text",
            description="Whether there is an email in the post's text or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["original_text"].str.match(r"\w+([\.-]?\w+)?@\w+([\.-]?\w+)?(\.\w{2,3})+").astype(int)


class PhoneNumberInText(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__phone_number_in_post_text",
            description="Whether there is a phone number in the post's text or not",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"].str.match(r"[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}").astype(int)
        )


class IsDescCounterfeit(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__is_desc_counterfeit",
            description="Whether the description is predicted as a counterfeit or not",
            default_value=-1,
            **kwargs,
        )

        # self.runner = PredictionRunner(
        #     model_name="is_desc_counterfeit_v1",
        #     feature_registry=FeatureRegistry(features=[PostTranslatedText(), PostOriginalText(), OrganisationName()]),
        # )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = 0

        # self.runner.predict(dataset=Dataset(posts=[post]))
        # return self.runner.prediction_df["Label_predicted"][0]


class WebsiteDomainName(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_website__domain_name",
            description="The domain name of the post's website",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["website.domain_name"]


class WebsiteCategory(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_website__website_category",
            description="The website category the post's website",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["website.website_category"].astype(str)


class PostTextWithoutOrganisation(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__text_without_organisation",
            description="The post text without the organisation name",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        # TODO: test
        posts[self.name] = ""
        # posts[self.name] = posts["original_text"].str.replace(posts["organisation.name"].str.replace("_", " "), "")


def get_vit_top_classification(n, images):
    predictions = []
    for image in images:
        if image["vit_predictions"] is None:
            continue

        predictions += [
            (category, probability) for category, probability in image["vit_predictions"].items() if probability
        ]

    sorted_predictions = sorted(predictions, key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
    return sorted_predictions[n - 1][0] if len(sorted_predictions) >= n else ""


def get_vit_top_prediction(n, images):
    predictions = []
    for image in images:
        if image["vit_predictions"] is None:
            continue

        predictions += [
            (category, probability) for category, probability in image["vit_predictions"].items() if probability
        ]

    sorted_predictions = sorted(predictions, key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
    return sorted_predictions[n - 1][1] if len(sorted_predictions) >= n else -1


def get_vit_all_classification(images):
    predictions = []
    for image in images:
        if image["vit_predictions"] is None:
            continue

        predictions += [
            (category, probability) for category, probability in image["vit_predictions"].items() if probability
        ]

    sorted_predictions = sorted(predictions, key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
    return " ".join([category for category, _ in sorted_predictions])


class TinyViT5M224Top1Classification(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_image__vit_top1_classification",
            description="The top1 classification of the post's image",
            default_value="",
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_top_classification(1, images))


class TinyViT5M224Top1Prediction(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_image__vit_top1_prediction",
            description="The top1 prediction of the post's image",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_top_prediction(1, images))


class TinyViT5M224Top2Classification(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_image__vit_top2_classification",
            description="The top2 classification of the post's image",
            default_value="",
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_top_classification(2, images))


class TinyViT5M224Top2Prediction(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_image__vit_top2_prediction",
            description="The top2 prediction of the post's image",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_top_prediction(2, images))


class TinyViT5M224Top3Classification(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_cat_image__vit_top3_classification",
            description="The top3 classification of the post's image",
            default_value="",
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_top_classification(3, images))


class TinyViT5M224Top3Prediction(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_image__vit_top3_prediction",
            description="The top3 prediction of the post's image",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_top_prediction(3, images))


class TinyViT5M224AllClassication(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_image__vit_all_classification",
            description="All vit classification of the post's image",
            default_value="",
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts["images"].apply(lambda images: get_vit_all_classification(images))


class PostOriginalTokenizedTextSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__original_tokenized_text_splited_by_ws_undcd",
            description="Tokenization of original post (split by whitespace)",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_whitespace)
            .apply(lambda x: " ".join(x))
        )


class PostTranslatedTokenizedTextSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__translated_tokenized_text_splited_by_ws_undcd",
            description="Tokenization of translated post (split by whitespace)",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_whitespace)
            .apply(lambda x: " ".join(x))
        )


class NumberOfOrganisationsInOriginalTokenSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_original_token_splited_by_ws_undcd",
            description="Number of organisations in post's original token (based on our clients) (split by whitespace)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_whitespace)
            .apply(self.count_keywords)
        )


class NumberOfOrganisationsInTranslatedTokenSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_translated_token_splited_by_ws_undcd",
            description="Number of organisations in post's translated token (based on our clients) (split by whitespace)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_whitespace)
            .apply(self.count_keywords)
        )


class OrganisationInOriginalTokenSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_original_token_splited_by_ws_undcd",
            description="Whether the organisation is in the post's token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = split_by_whitespace(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["original_text"]), axis=1
        )


class OrganisationInTranslatedTokenSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_translated_token_splited_by_ws_undcd",
            description="Whether the organisation is in the post's translated token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = split_by_whitespace(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["translated_text"]), axis=1
        )


class PostOriginalTokenizedTextRmvNaSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__original_tokenized_text_remove_non_an_splited_by_ws_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(remove_non_alphanumeric_split_by_whitespace)
            .apply(lambda x: " ".join(x))
        )


class PostTranslatedTokenizedTextRmvNaSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__translated_tokenized_text_remove_non_an_splited_by_ws_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(remove_non_alphanumeric_split_by_whitespace)
            .apply(lambda x: " ".join(x))
        )


class NumberOfOrganisationsInOriginalTokenRmvNaSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_original_token_remove_non_an_splited_by_ws_undcd",
            description="Number of organisations in post's token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(remove_non_alphanumeric_split_by_whitespace)
            .apply(self.count_keywords)
        )


class NumberOfOrganisationsInTranslatedTokenRmvNaSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_translated_token_remove_non_an_splited_by_ws_undcd",
            description="Number of organisations in post's translated token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(remove_non_alphanumeric_split_by_whitespace)
            .apply(self.count_keywords)
        )


class OrganisationInOriginalTokenRmvNaSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_original_token_remove_non_an_splited_by_ws_undcd",
            description="Whether the organisation is in the post's token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = remove_non_alphanumeric_split_by_whitespace(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["original_text"]), axis=1
        )


class OrganisationInTranslatedTokenRmvNaSplitedByWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_translated_token_remove_non_an_splited_by_ws_undcd",
            description="Whether the organisation is in the post's translated token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = remove_non_alphanumeric_split_by_whitespace(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["translated_text"]), axis=1
        )


class PostOriginalTokenizedTextSplitedByNonAnAndWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__original_tokenized_text_splited_by_non_an_and_ws_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace)
            .apply(lambda x: " ".join(x))
        )


class PostTranslatedTokenizedTextSplitedByNonAnAndWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__translated_tokenized_text_splited_by_non_an_and_ws_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace)
            .apply(lambda x: " ".join(x))
        )


class NumberOfOrganisationsInOriginalTokenSplitedByNonAnAndWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_original_token_splited_by_non_an_and_ws_undcd",
            description="Number of organisations in post's token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace)
            .apply(self.count_keywords)
        )


class NumberOfOrganisationsInTranslatedTokenSplitedByNonAnAndWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_translated_token_splited_by_non_an_and_ws_undcd",
            description="Number of organisations in post's translated token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace)
            .apply(self.count_keywords)
        )


class OrganisationInOriginalTokenSplitedByNonAnAndWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_original_token_splited_by_non_an_and_ws_undcd",
            description="Whether the organisation is in the post's token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = split_by_non_alphanumeric_and_whitespace(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["original_text"]), axis=1
        )


class OrganisationInTranslatedTokenSplitedByNonAnAndWsUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_translated_token_splited_by_non_an_and_ws_undcd",
            description="Whether the organisation is in the post's translated token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = split_by_non_alphanumeric_and_whitespace(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["translated_text"]), axis=1
        )


class PostOriginalTokenizedTextSplitedByNonAnAndWsAndBorderAlphaNumUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__original_tokenized_text_splited_by_non_an_and_ws_and_border_alpha_num_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric)
            .apply(lambda x: " ".join(x))
        )


class PostTranslatedTokenizedTextSplitedByNonAnAndWsAndBorderAlphaNumUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__translated_tokenized_text_splited_by_non_an_and_ws_and_border_alpha_num_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric)
            .apply(lambda x: " ".join(x))
        )


class NumberOfOrganisationsInOriginalTokenSplitedByNonAnAndWsAndBorderAlphaNumUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_original_token_splited_by_non_an_and_ws_and_border_alpha_num_undcd",
            description="Number of organisations in post's token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric)
            .apply(self.count_keywords)
        )


class NumberOfOrganisationsInTranslatedTokenSplitedByNonAnAndWsAndBorderAlphaNumUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_translated_token_splited_by_non_an_and_ws_and_border_alpha_num_undcd",
            description="Number of organisations in post's translated token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric)
            .apply(self.count_keywords)
        )


class OrganisationInOriginalTokenSplitedByNonAnAndWsAndBorderAlphaNumUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_original_token_splited_by_non_an_and_ws_and_border_alpha_num_undcd",
            description="Whether the organisation is in the post's token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["original_text"]), axis=1
        )


class OrganisationInTranslatedTokenSplitedByNonAnAndWsAndBorderAlphaNumUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_translated_token_splited_by_non_an_and_ws_and_border_alpha_num_undcd",
            description="Whether the organisation is in the post's translated token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = split_by_non_alphanumeric_and_whitespace_and_border_alpha_numeric(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["translated_text"]), axis=1
        )


class PostOriginalTokenizedTextRecstctFromFrgmtUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__original_tokenized_text_recstrct_from_frgmt_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(reconstruct_word_from_fragments)
            .apply(lambda x: " ".join(x))
        )


class PostTranslatedTokenizedTextRecstctFromFrgmtUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_text_post__translated_tokenized_text_recstrct_from_frgmt_undcd",
            description="Tokenization of post",
            default_value=-1,
            **kwargs,
        )

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(reconstruct_word_from_fragments)
            .apply(lambda x: " ".join(x))
        )


class NumberOfOrganisationsInOriginalTokenRecstctFromFrgmtUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_original_token_recstrct_from_frgmt_undcd",
            description="Number of organisations in post's token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["original_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(reconstruct_word_from_fragments)
            .apply(self.count_keywords)
        )


class NumberOfOrganisationsInTranslatedTokenRecstctFromFrgmtUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post__organisations_number_in_post_translated_token_recstrct_from_frgmt_undcd",
            description="Number of organisations in post's translated token (based on our clients)",
            default_value=-1,
            **kwargs,
        )

    def count_keywords(self, token_list: List[str]) -> int:
        count = 0
        organisation_pieces = [o.lower().split("_") for o in ORGANISATIONS]
        for org in organisation_pieces:
            common_words = set(org) & set(token_list)
            if len(common_words) == len(org):
                count += 1
        return count

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = (
            posts["translated_text"]
            .apply(basic_conversion)
            .str.lower()
            .apply(reconstruct_word_from_fragments)
            .apply(self.count_keywords)
        )


class OrganisationInOriginalTokenRecstctFromFrgmtUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_original_token_recstrct_from_frgmt_undcd",
            description="Whether the organisation is in the post's token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = reconstruct_word_from_fragments(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["original_text"]), axis=1
        )


class OrganisationInTranslatedTokenRecstctFromFrgmtUndcd(Feature):
    def __init__(self, **kwargs):
        super().__init__(
            name="f_num_post_organisation__organisation_in_post_translated_token_recstrct_from_frgmt_undcd",
            description="Whether the organisation is in the post's translated token or not",
            default_value=-1,
            **kwargs,
        )

    def org_is_in_text(self, org_name: str, raw_text: str) -> bool:
        if org_name == "Chanel_Navee":
            org_name = "Chanel"
        org = org_name.lower().split("_")
        text = basic_conversion(raw_text)
        text = text.lower()
        token_list = reconstruct_word_from_fragments(text)
        common_words = set(org) & set(token_list)
        return len(common_words) == len(org)

    def df_to_feature(self, posts: pd.DataFrame):
        posts[self.name] = posts.apply(
            lambda row: self.org_is_in_text(row["organisation.name"], row["translated_text"]), axis=1
        )
