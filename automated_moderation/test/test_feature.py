import pytest
from automated_moderation.feature import Feature


class TestFeature:
    @staticmethod
    @pytest.mark.parametrize(
        "name,tags",
        [
            ("f_num_post__abc_def", set()),
            ("f_cat_post__abc", set()),
            ("f_cat_account__myfeaturename", set()),
            ("f_cat_account__myfeaturewithtags", {"tg_public", "tg_deprecated"}),
        ],
    )
    def test_feature_init_correct(name, tags):
        Feature(name, tags=tags)

    @staticmethod
    @pytest.mark.parametrize(
        "name,tags",
        [
            ("bad_name", set()),
            ("g_cat_post__bad_prefix", set()),
            ("g_badtype_post__abc", set()),
            ("g_num_badattribution__abc", set()),
            ("f_cat_account__name with spaces", set()),
            ("f_cat_account__badtag", {"tg_asdfdas"}),
        ],
    )
    def test_feature_init_incorrect(name, tags):
        with pytest.raises(Exception):
            Feature(name, tags=tags)

    @staticmethod
    @pytest.mark.parametrize(
        "name,tags,include_tags,exclude_tags,result",
        [
            ("f_num_post__a", set(), {"tg_public"}, {"tg_deprecated"}, False),
            ("f_num_post__a", {"tg_deprecated"}, {"tg_public"}, {"tg_deprecated"}, False),
            ("f_num_post__a", {"tg_public"}, {"tg_public"}, set(), True),
            ("f_num_post__a", {"tg_public"}, {"tg_public"}, {"tg_deprecated"}, True),
            ("f_num_post__a", {"tg_public", "tg_deprecated"}, {"tg_public"}, {"tg_deprecated"}, False),
            ("f_num_post__a", {"tg_public", "tg_deprecated"}, {"tg_public", "tg_deprecated"}, set(), True),
        ],
    )
    def test_feature_filter_tags(name, tags, include_tags, exclude_tags, result):
        assert Feature(name, tags=tags).is_good_for_tags(include_tags, exclude_tags) == result
