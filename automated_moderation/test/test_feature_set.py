import pytest
from automated_moderation.feature.registry import FeatureRegistry
from automated_moderation.feature.set import EnumeratedFeatureSet


def get_sample_registry():
    result = FeatureRegistry()
    result.add("f_num_post__none", tags=set())
    result.add("f_num_post__deprecated", tags={"tg_deprecated"})
    result.add("f_num_post__public", tags={"tg_public"})
    result.add("f_num_post__public_deprecated", tags={"tg_public", "tg_deprecated"})
    result.add("f_cat_post__none", tags=set())
    result.add("f_cat_post__deprecated", tags={"tg_deprecated"})
    result.add("f_cat_post__public", tags={"tg_public"})
    result.add("f_cat_post__public_deprecated", tags={"tg_public", "tg_deprecated"})
    return result


class TestEnumeratedFeatureSet:
    @staticmethod
    @pytest.mark.parametrize(
        "include_tags,exclude_tags,result",
        [
            (
                {"tg_all"},
                set(),
                (
                    "0\tLabel\tf_label\n"
                    "1\tNum\tf_num_post__none\n"
                    "2\tNum\tf_num_post__deprecated\n"
                    "3\tNum\tf_num_post__public\n"
                    "4\tNum\tf_num_post__public_deprecated\n"
                    "5\tCateg\tf_cat_post__none\n"
                    "6\tCateg\tf_cat_post__deprecated\n"
                    "7\tCateg\tf_cat_post__public\n"
                    "8\tCateg\tf_cat_post__public_deprecated\n"
                ),
            ),
            (
                {"tg_public"},
                {"tg_deprecated"},
                ("0\tLabel\tf_label\n" "1\tNum\tf_num_post__public\n" "2\tCateg\tf_cat_post__public\n"),
            ),
        ],
    )
    def test_cd(tmp_path, include_tags, exclude_tags, result):
        out = tmp_path / "out.cd"

        efs = EnumeratedFeatureSet(get_sample_registry().get_slice(include_tags, exclude_tags))
        efs.create_columns_description(out)

        print(out.read_text())
        assert out.read_text() == result
