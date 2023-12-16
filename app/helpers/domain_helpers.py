import whois
from builtwith import builtwith
from app.dao import RedisDAO

redis_DAO = RedisDAO()


def get_domain_web_stack(domain_name):
    """
    domain_name : shoppee.tw
    returns the tech stack used in the website if available
    """
    try:

        built_with = redis_DAO.get_domain_built_with(domain_name)
        if built_with is not None:
            print(f"Returning Cached Built With for {domain_name}")
            return built_with

        parsed_domain_url = f"https://{domain_name}" if "http" not in domain_name else domain_name
        domain_info = builtwith(parsed_domain_url)

        redis_DAO.set_domain_name_built_with(domain_name, domain_info)
        return domain_info
    except Exception as ex:
        print(f"Error Processing get_domain_web_stack for domain_name {domain_name}. Exception {ex}")
        return None


def get_domain_who_is(domain_name):
    """
    url : http://shoppee.tw
    returns the who is info
    """
    try:
        who_is = redis_DAO.get_domain_who_is(domain_name)
        if who_is is not None:
            print(f"Returning Cached who_is for {domain_name}")
            return who_is

        who_is_info = whois.whois(domain_name)
        who_is = {}
        ## add all information
        who_is["complete_meta"] = who_is_info.text

        ## parse the data
        for key, value in who_is_info.items():
            ## for dates save only one date for each field
            if key in ("creation_date", "expiration_date", "updated_date"):
                if type(value) == list:
                    who_is[key] = str(value[0])
                else:
                    who_is[key] = str(value)
            elif type(value) == list:
                who_is[key] = [str(item) for item in value]
            else:
                who_is[key] = str(value)

        redis_DAO.set_domain_name_who_is(domain_name, who_is)
        return who_is
    except Exception as ex:
        print(f"Error Processing get_domain_who_is for domain_name {domain_name}. Exception {ex}")
        return None
