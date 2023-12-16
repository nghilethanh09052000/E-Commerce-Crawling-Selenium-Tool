from jsonpath_ng import parse
import re
from app.settings import sentry_sdk
from app import logger
from selenium_driver.helpers.s3 import upload_image_from_url


def get_json_pictures(response, config):
    """Get Images from JSON"""
    is_json_obj = config.is_json_obj
    if is_json_obj:
        image_urls = get_json_obj(response, config)
    else:
        image_urls = get_json_value(response, config)
    uploaded_results = []
    if not image_urls:
        return uploaded_results
    for image_url in image_urls:
        if image_url.startswith("//") and "http" not in image_url:
            image_url = f"https:{image_url}"
        s3_url, is_blacklisted = upload_image_from_url(image_url)
        if is_blacklisted:
            continue
        uploaded_results.append({"s3_url": s3_url, "picture_url": image_url})

    return uploaded_results


def remove_html_tags(text):
    try:
        clean = re.compile("<.*?>")
        return re.sub(clean, "", text)
    except Exception as ex:
        logger.info(f"Exception on remove_html_tags : {str(ex)}")
        sentry_sdk.capture_exception(ex)
        return ""


def get_json_obj(response, config):
    """Use jsonpath_ng to extract json object from api response"""
    try:
        attribute_names = config.attribute_names
        return_list = config.return_list

        results = []
        for attribute_name in attribute_names:
            jsonpath_expr = parse(attribute_name)
            values = [match.value for match in jsonpath_expr.find(response)]
            if values:
                if return_list:
                    results.extend(values)
                else:
                    results.extend(values[0])
        return results
    except Exception as ex:
        logger.info(f"Error Parsing {config} from response {response} : {str(ex)}")
        sentry_sdk.capture_exception(ex)


def get_json_value(response, config):
    """Use jsonpath_ng to extract json fields from api response"""
    try:
        attribute_names = config.attribute_names
        return_list = config.return_list
        replace_old = config.replace_old
        replace_new = config.replace_new
        is_regex_replace = config.is_regex_replace
        append_text = config.append_text
        clean_html = config.clean_html
        results = []
        for attribute_name in attribute_names:
            jsonpath_expr = parse(attribute_name)
            values = [str(match.value) for match in jsonpath_expr.find(response)]
            if values:
                if clean_html:
                    values = [remove_html_tags(value) for value in values]

                if return_list:
                    results.extend(values)
                else:
                    results.append(values[0])

        if replace_old and replace_new:
            if not is_regex_replace:
                results = [result.replace(replace_old, replace_new) for result in results]
            else:
                results = [re.sub(replace_old, replace_new, result) for result in results]

        ## Case when we have to add currency manually
        if append_text:
            results.append(append_text)

        ## return text value ,example price + curerency
        if not results:
            return None

        # incase of retuning list of images
        if return_list:
            return results

        return " ".join(results)
    except Exception as ex:
        logger.info(f"Error Parsing {config} from response {response} : {str(ex)}")
        sentry_sdk.capture_exception(ex)
