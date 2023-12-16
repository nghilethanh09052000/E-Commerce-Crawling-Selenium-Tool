import importlib
from .registry import FeatureRegistry
from .features_list import (
    OrganisationName,
    LogoDetected,
    Hashtags,
    HashtagsNumber,
    PostCategory,
    InfringingKeywordCount,
    PostTranslatedText,
    PostOriginalText,
    PostTextWithoutOrganisation,
    IsPosterKnown,
    PosterInfringingNumberForAllOrganisations,
    PosterInfringingNumberForOrganisation,
    PosterInfringingPercentForAllOrganisations,
    PosterInfringingPercentForOrganisation,
    PosterPostNumberForAllOrganisations,
    PosterPostNumberForOrganisation,
    ClusterInfringingNumberForAllOrganisations,
    ClusterInfringingNumberForOrganisation,
    ClusterInfringingPercentForAllOrganisations,
    ClusterInfringingPercentForOrganisation,
    ClusterPostNumberForAllOrganisations,
    ClusterPostNumberForOrganisation,
    OrganisationInOriginalText,
    OrganisationInTranslatedText,
    NumberOfOrganisationsInOriginalText,
    NumberOfOrganisationsInTranslatedText,
    OrganisationInPosterName,
    NumberOfOrganisationsInPosterName,
    NumberOfOrganisationsInHashtags,
    OrganisationInHashtags,
    EmailInText,
    PhoneNumberInText,
    IsDescCounterfeit,
    WebsiteDomainName,
    WebsiteCategory,
    TinyViT5M224Top1Classification,
    TinyViT5M224AllClassication,
    TinyViT5M224Top1Prediction,
    TinyViT5M224Top2Classification,
    TinyViT5M224Top2Prediction,
    TinyViT5M224Top3Classification,
    TinyViT5M224Top3Prediction,
)


FEATURE_REGISTRY = FeatureRegistry()

FEATURE_REGISTRY.add_features(
    TinyViT5M224Top1Classification(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    TinyViT5M224AllClassication(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    TinyViT5M224Top1Prediction(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    TinyViT5M224Top2Classification(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    TinyViT5M224Top2Prediction(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    TinyViT5M224Top3Classification(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    TinyViT5M224Top3Prediction(tags={"tg_unimplemented", "tg_need_first_image", "tg_need_vit"}),
    OrganisationName(tags={"tg_public", "tg_need_search_results"}),
    LogoDetected(tags={"tg_public", "tg_need_search_results", "tg_need_first_image"}),
    Hashtags(tags={"tg_public", "tg_need_search_results", "tg_instagram"}),
    HashtagsNumber(tags={"tg_public", "tg_need_search_results"}),
    PostOriginalText(tags={"tg_public", "tg_need_search_results"}),
    PostTextWithoutOrganisation(tags={"tg_unimplemented", "tg_need_search_results"}),
    PostTranslatedText(tags={"tg_public", "tg_need_search_results", "tg_need_translation"}),
    InfringingKeywordCount(tags={"tg_public", "tg_need_search_results", "tg_need_translation"}),
    IsPosterKnown(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PosterInfringingNumberForAllOrganisations(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PosterInfringingNumberForOrganisation(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PosterInfringingPercentForAllOrganisations(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PosterInfringingPercentForOrganisation(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PosterPostNumberForAllOrganisations(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PosterPostNumberForOrganisation(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    ClusterInfringingNumberForAllOrganisations(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    ClusterInfringingNumberForOrganisation(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    ClusterInfringingPercentForAllOrganisations(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    ClusterInfringingPercentForOrganisation(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    ClusterPostNumberForAllOrganisations(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    ClusterPostNumberForOrganisation(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    PostCategory(tags={"tg_implemented", "tg_need_search_results", "tg_need_first_image", "tg_need_classification"}),
    OrganisationInOriginalText(tags={"tg_public", "tg_need_search_results"}),
    OrganisationInTranslatedText(tags={"tg_public", "tg_need_search_results", "tg_need_translation"}),
    NumberOfOrganisationsInOriginalText(tags={"tg_public", "tg_need_search_results"}),
    NumberOfOrganisationsInTranslatedText(tags={"tg_public", "tg_need_search_results", "tg_need_translation"}),
    OrganisationInPosterName(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    NumberOfOrganisationsInPosterName(tags={"tg_implemented", "tg_need_search_results", "tg_need_history"}),
    NumberOfOrganisationsInHashtags(tags={"tg_public", "tg_need_search_results"}),
    OrganisationInHashtags(tags={"tg_public", "tg_need_search_results"}),
    EmailInText(tags={"tg_public", "tg_need_search_results"}),
    PhoneNumberInText(tags={"tg_public", "tg_need_search_results"}),
    IsDescCounterfeit(tags={"tg_implemented", "tg_need_search_results"}),
    WebsiteDomainName(
        tags={
            "tg_public",
        }
    ),
    WebsiteCategory(
        tags={
            "tg_implemented",
        }
    ),
)

# import classes which has similar name
class_basic_name = [
    "PostOriginalTokenizedText",
    "PostTranslatedTokenizedText",
    "NumberOfOrganisationsInOriginalToken",
    "NumberOfOrganisationsInTranslatedToken",
    "OrganisationInOriginalToken",
    "OrganisationInTranslatedToken",
]
text_tokenization_name = [
    # "SplitedByWs",
    # "RmvNaSplitedByWs",
    # "SplitedByNonAnAndWs",
    # "SplitedByNonAnAndWsAndBorderAlphaNum",
    "RecstctFromFrgmt",
]
text_conversion_name = ["Undcd"]
module_name = ".features_list"
module = importlib.import_module(module_name, package="automated_moderation.feature")
for basic_name in class_basic_name:
    for token_name in text_tokenization_name:
        for conv_name in text_conversion_name:
            name = basic_name + token_name + conv_name
            globals()[name] = getattr(module, name)
            if "Original" in name:
                FEATURE_REGISTRY.add_features(globals()[name](tags={"tg_public", "tg_need_search_results"}))
            elif "Translated" in name:
                FEATURE_REGISTRY.add_features(
                    globals()[name](tags={"tg_public", "tg_need_search_results", "tg_need_translation"})
                )
