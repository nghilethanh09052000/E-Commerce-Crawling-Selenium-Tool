import pytest
from navee_utils.domain_helper import get_domain_name_from_url

post_url_to_domain_name = [
    # Randomly selected URLs from the database
    ("http://www.tbags.ru/index.php?id=489836", "tbags.ru"),
    (
        "https://www.bol.com/nl/nl/p/60-x-80-cm-glasschilderij-doodskop-gucci-met-goudfolie/9300000143636225/",
        "bol.com",
    ),
    (
        "https://www.etsy.com/listing/657917316/18k-white-gold-diamond-mariner-link",
        "etsy.com",
    ),
    (
        "https://am.olx.com.br/sao-paulo-e-regiao/bijouteria-relogios-e-acessorios/relogio-gucci-sem-uso-troco-por-apple-watch-volto-grana-1107448262",
        "olx.com.br",
    ),
    ("https://item.fril.jp/6a020166c0d0348d2d2e71dd1ef32413", "fril.jp"),
    (
        "https://www.avito.ru/kaluga/krasota_i_zdorove/parfum_gucci_flora_euro_kachestvo_3270835380",
        "avito.ru",
    ),
    (
        "https://shopee.vn/T%C3%BAi-%C4%91eo-ch%C3%A9o-th%E1%BB%9Di-trang-th%E1%BB%83-thao-GUCCCI-i.93018591.13686122685",
        "shopee.vn",
    ),
    (
        "https://shopee.com.br/2023-Novo-Celine-Mini-Saco-De-Ombro-Feminino-ATMJ-8FFS-LV-Gucci-Chanel-Hermes-YSL-Fendi-i.1027204029.19298940224",
        "shopee.com.br",
    ),
    ("https://www.ebay.com/itm/134688036959", "ebay.com"),
    ("https://balaan.co.kr/shop/goods/goods_view.php?goodsno=44800314", "balaan.co.kr"),
    ("https://item.rakuten.co.jp/nopple/sw-gg0800sa-002", "rakuten.co.jp"),
    ("https://www.instagram.com/p/BWcbsj4hGLE", "instagram.com"),
    (
        "https://zakupka.com/uk/p/1130765250-falling-in-love-with-neroli-iris-avon",
        "zakupka.com",
    ),
    ("https://item.fril.jp/520d7762253daae9e7255c2e6c24feac", "fril.jp"),
    ("https://item.rakuten.co.jp/jumblestore/2343440252089", "rakuten.co.jp"),
    ("https://www.instagram.com/p/CcjxOsbMdIz", "instagram.com"),
    ("http://it.abags.cn/index.php?id=525171", "abags.cn"),
    ("https://www.olx.kz/d/obyavlenie/sumka-gucci-nedorogo-IDo8ODU.html", "olx.kz"),
    (
        "https://shopee.com.my/Gucci!-New-Fashion-Sumptuous-Unisex-Shopping-Essentials-Bucket-Hats-Ready-Stock!-i.418948181.21927317236",
        "shopee.com.my",
    ),
    (
        "https://shopee.com.br/Cintur%C3%A3o-de-couro-de-mulheres-de-marca-luxuosa-2-4-cm-Hermes-(com-caixa-de-embalagem)-i.957672709.23930999530",
        "shopee.com.br",
    ),
    # Edge cases
    ("https://au.carousell.com/p/1174217562", "au.carousell.com"),
    (
        "https://www.olx.sa.com/ad/gucci-ophidia-gg-mini-bag-ID110179721.html",
        "olx.sa.com",
    ),
    ("https://www.facebook.com/541310081133696", "facebook.com"),
    (
        "https://web.facebook.com/marketplace/item/840099987688418",
        "facebook.com/marketplace",
    ),
    (
        "https://www.facebook.com/marketplace/item/800535748744375",
        "facebook.com/marketplace",
    ),
]


class TestDomainHelper:
    @staticmethod
    @pytest.mark.parametrize("post_url, domain_name", post_url_to_domain_name)
    def test_get_domain_from_url(post_url, domain_name):
        assert get_domain_name_from_url(post_url) == domain_name
