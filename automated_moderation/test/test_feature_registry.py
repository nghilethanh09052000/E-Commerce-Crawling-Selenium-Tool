import pytest
from automated_moderation.feature.registry import FeatureRegistry


def get_sample_registry():
    result = FeatureRegistry()
    result.add("f_num_post__none", tags=set())
    result.add("f_num_post__deprecated", tags={"tg_deprecated"})
    result.add("f_num_post__public", tags={"tg_public"})
    result.add("f_num_post__public_deprecated", tags={"tg_public", "tg_deprecated"})
    return result


class TestFeatureRegistry:
    @staticmethod
    def test_duplicates():
        with pytest.raises(Exception):
            r = FeatureRegistry()
            r.add("f_num_post__none")
            r.add("f_num_post__none")

    @staticmethod
    @pytest.mark.parametrize(
        "include_tags,exclude_tags,result",
        [
            (set(), set(), set()),
            (
                {"tg_all"},
                set(),
                {"f_num_post__none", "f_num_post__deprecated", "f_num_post__public", "f_num_post__public_deprecated"},
            ),
            ({"tg_public"}, set(), {"f_num_post__public", "f_num_post__public_deprecated"}),
            ({"tg_public"}, {"tg_deprecated"}, {"f_num_post__public"}),
        ],
    )
    def test_slice(include_tags, exclude_tags, result):
        s = get_sample_registry().get_slice(include_tags, exclude_tags)
        assert set((f for f in s.keys())) == result
