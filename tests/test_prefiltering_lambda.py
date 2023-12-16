from app.service.filter.filter_search_results_marketplaces import filter_marketplace_search_results
from app.models import Organisation, Website, Session

if __name__ == "__main__":
    posts = {
        "Miracle-girl-m-magic-and-strange-clothing-the-yo-yo-girls-dress-red-wave-point-ladybu%E5%A5%87%E8%BF%B9%E5%B0%91%E5%A5%B3%E7%B1%B3%E5%8F%AF%E5%B9%BB%E5%A5%87%E6%9C%8D%E8%A3%85%E6%82%A0%E6%82%A0%E7%90%83%E5%A5%B3%E7%AB%A5%E7%BA%A2%E8%89%B2%E6%B3%A2%E7%82%B9%E8%BF%9E%E8%A1%A3%E8%A3%99%E7%93%A2%E8%99%AB%E9%9B%B7%E8%BF%AA%E8%A1%A3%E6%9C%8D-7830-i.393450188.23479264620": {
            "light_post_log_id": 39167259,
            "id": "Miracle-girl-m-magic-and-strange-clothing-the-yo-yo-girls-dress-red-wave-point-ladybu%E5%A5%87%E8%BF%B9%E5%B0%91%E5%A5%B3%E7%B1%B3%E5%8F%AF%E5%B9%BB%E5%A5%87%E6%9C%8D%E8%A3%85%E6%82%A0%E6%82%A0%E7%90%83%E5%A5%B3%E7%AB%A5%E7%BA%A2%E8%89%B2%E6%B3%A2%E7%82%B9%E8%BF%9E%E8%A1%A3%E8%A3%99%E7%93%A2%E8%99%AB%E9%9B%B7%E8%BF%AA%E8%A1%A3%E6%9C%8D-7830-i.393450188.23479264620",
            "url": "https://shopee.sg/Miracle-girl-m-magic-and-strange-clothing-the-yo-yo-girls-dress-red-wave-point-ladybu%E5%A5%87%E8%BF%B9%E5%B0%91%E5%A5%B3%E7%B1%B3%E5%8F%AF%E5%B9%BB%E5%A5%87%E6%9C%8D%E8%A3%85%E6%82%A0%E6%82%A0%E7%90%83%E5%A5%B3%E7%AB%A5%E7%BA%A2%E8%89%B2%E6%B3%A2%E7%82%B9%E8%BF%9E%E8%A1%A3%E8%A3%99%E7%93%A2%E8%99%AB%E9%9B%B7%E8%BF%AA%E8%A1%A3%E6%9C%8D-7830-i.393450188.23479264620",
            "tags": ["search_query:瓢蟲少女"],
            "price": "SGD21.46 - SGD31.08",
            "title": "Miracle girl m magic and strange clothing the yo-yo girls dress red wave point ladybu奇迹少女米可幻奇服装悠悠球女童红色波点连衣裙瓢虫雷迪衣服 7830",
            "vendor": None,
            "videos": None,
            "location": "Mainland China",
            "pictures": [
                {
                    "s3_url": "https://s3-eu-west-1.amazonaws.com/specific-scraper-production/images/ee7a03c21656899b0760768be33d547831a05482d36bb68408fa6dcb562a0ce4.jpeg",
                    "picture_url": "https://down-sg.img.susercontent.com/file/sg-11134201-7rbk0-lkz0ztf4vcc189_tn",
                }
            ],
            "ships_to": None,
            "item_sold": None,
            "search_url": "https://shopee.sg/search?keyword=瓢蟲少女&sortBy=ctime",
            "ships_from": None,
            "description": None,
            "loaded_page": 1,
            "poster_link": None,
            "archive_link": None,
            "posting_time": None,
            "index_on_page": 1,
            "scraping_time": "2023-09-06-09:17:25",
            "organisation_names": ["Zagtoon"],
        }
    }

    model_name = "marketplace_v3"

    with Session() as session:
        organisation = session.query(Organisation).filter(Organisation.name == "Zagtoon").one()
        website = session.query(Website).filter(Website.domain_name == "shopee.sg").one()

    filter_marketplace_search_results(
        posts,
        organisation=organisation,
        website=website,
        sample=False,
    )
