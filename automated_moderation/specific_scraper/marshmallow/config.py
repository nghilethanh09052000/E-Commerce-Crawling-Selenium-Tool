from typing import List

from marshmallow import fields

from . import CustomSchema

DEFAULT_SCROLL_PAUSE_TIME = 5
DEFAULT_LOADING_DELAY = 5
DEFAULT_SLEEP_AFTER_GET = 5
DEFAULT_SCROLL_SLEEP = 5
DEFAULT_SLEEP_AFTER_OPERATIONS = 5
DEFAULT_REQUIRED_LOADING_DELAY = 5
DEFAULT_REQUIRED_LOADING_TIMEOUT = 5
DEFAULT_LOADING_TIMEOUT = 5
DEFAULT_CLOUDFLARE_BYPASS_TIME = 5


"""
On the difference between loading_delay and loading_timeout
  * loading_delay is used for rigid sleeps that slow down the scraping even when the actual loading is fast. It's important to keep them small.
  * loading_timeout is used for WebDriverWait and slows down the loading only when it's necessary (e.g. slow connection). They can be more liberal.
"""


class DriverInitializationModuleSchema(CustomSchema):
    """Schema Settings to Load the driver"""

    name = fields.Str()
    start_maximized = fields.Boolean(default=False, missing=False)
    headless = fields.Boolean(default=True, missing=True)
    xvfb = fields.Boolean(default=False, missing=False)
    load_images = fields.Boolean(default=False, missing=False)
    take_screenshot = fields.Boolean(default=False, missing=False)
    cookies = fields.Raw(default=None, missing=None)
    override_user_agent = fields.Boolean(default=False, missing=False)
    use_tor_proxy = fields.Boolean(default=False, missing=False)
    stealth_driver = fields.Boolean(default=False, missing=False)
    mobile_driver = fields.Boolean(default=False, missing=False)
    undetected_driver = fields.Boolean(default=True, missing=True)
    driver_timeout = fields.Integer(default=None, missing=None)
    cloudflare_bypass = fields.Boolean(default=False, missing=False)
    cloudflare_bypass_time = fields.Float(default=None, missing=DEFAULT_CLOUDFLARE_BYPASS_TIME)
    page_load_strategy = fields.Str(default=None, missing=None)
    loading_delay = fields.Float(default=DEFAULT_LOADING_DELAY, missing=DEFAULT_LOADING_DELAY)
    chromeprofile_domain_name = fields.Str(default=None, missing=None)
    chromeprofile_name = fields.Str(default=None, missing=None)
    load_offline_driver = fields.Bool(default=False, missing=False)


class SearchPageURLBuilderModuleSchema(CustomSchema):
    """Schema to build search urls"""

    name = fields.Str()
    search_page_url_templates = fields.List(fields.Str())


class UrlExtractionSchema(CustomSchema):
    """Schema for extracting URL from a URL parameter"""

    url_parameter = fields.Str(missing=None)
    extract_if_match_regex = fields.Str(missing=None)


class UrlCleaningSchema(CustomSchema):
    """Schema for post/poster saving module"""

    query_string_to_keep = fields.List(fields.Str(), default=[], missing=[])
    skip_query_string_cleaning = fields.Boolean(default=False, missing=False)
    localisation_country_list = fields.List(fields.Str(), missing=None)
    extract_url_from_string_parameter: UrlExtractionSchema = fields.Nested(UrlExtractionSchema(), missing=None)


class IdentifierRetrieverModuleSchema(CustomSchema):
    """Schema to retrieve identfifiers"""

    name = fields.Str()
    css_selector = fields.Raw(missing=None)
    css_selectors = fields.List(fields.Raw(), missing=None)
    stop_css_selector = fields.Str(default=None, missing=None)
    stop_value = fields.Str(default=None, missing=None)
    stop_attribute_name = fields.Str(default=None, missing=None)
    elem_text_contains = fields.Str(missing=None)
    regex = fields.Str(missing=None)
    regex_substitute = fields.Str(missing=None)
    regex_substitute_string = fields.Str(missing=None)
    loading_delay = fields.Float(default=DEFAULT_LOADING_DELAY, missing=DEFAULT_LOADING_DELAY)
    loading_timeout = fields.Float(default=DEFAULT_LOADING_TIMEOUT, missing=DEFAULT_LOADING_TIMEOUT)
    ## # TODO: simplify the fields being used here *
    output_string = fields.Str(missing=None)
    attribute_name = fields.Str(missing=None)
    key_css_selector = fields.Str(missing=None)
    value_css_selector = fields.Str(missing=None)
    picture_css_selector = fields.Str(missing=None)
    undetected_click = fields.Boolean(missing=False)
    clickable_css_selector = fields.Raw(missing=None)
    clickable_css_selector_1 = fields.Str(missing=None)
    clickable_css_selector_2 = fields.Str(missing=None)
    hover_before_click_css_selector = fields.Str(missing=None)
    escape_popup_on_end = fields.Boolean(missing=False)
    click_opens_new_tab = fields.Boolean(missing=False)
    scroll_down_before_click = fields.Boolean(default=False, missing=False)
    scroll_pause_time = fields.Integer(missing=DEFAULT_SCROLL_PAUSE_TIME)
    scroll_range = fields.Integer(default=1, missing=1)
    after_pause_time = fields.Integer(default=1, missing=1)
    before_pause_time = fields.Integer(default=1, missing=1)
    requires_url_update = fields.Boolean(default=False, missing=False)
    fixed_scroll_to = fields.Str(missing=None)
    scroll_up = fields.Boolean(default=False, missing=False)
    close_alert = fields.Boolean(default=False, missing=False)
    skip_xdg_open_window = fields.Boolean(default=False, missing=False)
    replace_old = fields.Str(missing=None)
    replace_new = fields.Str(missing=None)
    is_regex_replace = fields.Boolean(default=False, missing=False)
    has_multiple_items_in_same_selector = fields.Boolean(default=False, missing=False)
    exclude_children = fields.Boolean(default=False, missing=False)
    trim_text = fields.Boolean(default=False, missing=False)
    input_format = fields.Str(default=None, missing=None)
    output_format = fields.Str(default=None, missing=None)
    post_url_cleaning_module: UrlCleaningSchema = fields.Nested(UrlCleaningSchema(), missing=None)
    clickable_css_is_always_present = fields.Boolean(default=True, missing=True)
    key_regex = fields.Raw(default=None, missing=None)
    value_regex = fields.Raw(default=None, missing=None)
    key_css_selector_attribute_name = fields.Str(default=None, missing=None)
    value_css_selector_attribute_name = fields.Str(default=None, missing=None)
    key_replace_old = fields.Str(default=None, missing=None)
    key_replace_new = fields.Str(default=None, missing=None)
    key_replace_new = fields.Str(default=None, missing=None)
    value_replace_old = fields.Str(default=None, missing=None)
    value_replace_new = fields.Str(default=None, missing=None)
    remove_if_match_regex = fields.Str(default=None, missing=None)
    key_css_selectors = fields.List(fields.Str(), missing=None)
    value_css_selectors = fields.List(fields.Str(), missing=None)
    key_attributes = fields.List(fields.Str(), missing=None)
    value_attributes = fields.List(fields.Str(), missing=None)
    clickable_css_selectors = fields.Raw(default=None, missing=None)
    attribute_name_1 = fields.Str(default=None, missing=None)
    attribute_name_2 = fields.Str(default=None, missing=None)
    replace_old_regex = fields.Str(default=None, missing=None)
    key_atributes = fields.Raw(default=None, missing=None)
    css_selector_2 = fields.Str(default=None, missing=None)
    regex_1 = fields.Str(default=None, missing=None)
    replace_new_1 = fields.Str(default=None, missing=None)
    replace_old_1 = fields.Str(default=None, missing=None)
    css_selector_1 = fields.Str(default=None, missing=None)
    css_selector_1 = fields.Str(default=None, missing=None)
    title_column_name = fields.Str(default=None, missing=None)
    move_to_element_before_click = fields.Boolean(default=False, missing=False)
    xpath = fields.Str(default=None, missing=None)
    json_attribute_name = fields.Str(default=None, missing=None)
    button_css_selector = fields.Str(default=None, missing=None)
    close_button_css_selector = fields.Str(default=None, missing=None)
    skip_query_string_cleaning = fields.Boolean(default=False, missing=False)
    replace_tail = fields.Str(default=None, missing=None)
    attribute_names = fields.List(fields.Raw(), missing=None)
    clean_html = fields.Boolean(default=False, missing=False)
    json_index = fields.Integer(default=None, missing=0)
    draggable_css_selector = fields.Str(default=None, missing=None)
    restart_button_css_selector = fields.Str(default=None, missing=None)
    iframe_css_selector = fields.Str(default=None, missing=None)
    attempts_count = fields.Integer(default=None, missing=None)
    slider_box_size = fields.Integer(default=None, missing=None)
    slider_bar_size = fields.Integer(default=None, missing=None)
    suffix_substring = fields.Str(default=None, missing=None)
    split_substring = fields.Str(default=None, missing=None)
    skip_video = fields.Boolean(default=False, missing=False)
    append_text = fields.Str(missing=None)
    return_list = fields.Boolean(default=False, missing=False)
    value = fields.Str(missing=None)
    restart_driver = fields.Boolean(missing=False)


class RequiredIdentifierRetrieverModuleSchema(IdentifierRetrieverModuleSchema):
    """Schema to retrieve required identifiers (like title and price). Better to wait longer than to fail"""

    loading_delay = fields.Float(default=DEFAULT_REQUIRED_LOADING_DELAY, missing=DEFAULT_REQUIRED_LOADING_DELAY)
    loading_timeout = fields.Float(default=DEFAULT_REQUIRED_LOADING_TIMEOUT, missing=DEFAULT_REQUIRED_LOADING_TIMEOUT)


class APIRequestModule(CustomSchema):
    """Schema for login module"""

    post_body = fields.String(default=None, missing=None)
    method_type = fields.String(default=None, missing=None)
    api_headers = fields.String(default=None, missing=None)


class BasePostIdentifiersListModuleSchema(CustomSchema):
    """Schema of identifier used for posts"""

    action_before_poster_post_identifiers_module: List[RequiredIdentifierRetrieverModuleSchema] = fields.List(
        fields.Nested(RequiredIdentifierRetrieverModuleSchema), missing=None
    )

    listing_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    title_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    description_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    price_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    stock_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    vendor_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    poster_link_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    ships_from_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    ships_to_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    pictures_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    videos_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    date_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    location_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    item_sold_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    post_url_cleaning_module: UrlCleaningSchema = fields.Nested(UrlCleaningSchema(), missing=None)

    api_request_params = fields.Nested(APIRequestModule(), missing=None)


class PosterPostRetreivalModuleSchema(BasePostIdentifiersListModuleSchema, IdentifierRetrieverModuleSchema):
    """Schema for poster page browsing"""

    post_url_cleaning_module: UrlCleaningSchema = fields.Nested(UrlCleaningSchema(), missing=None)
    load_more_results_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    listing_container_css_selector = fields.Str(default=None, missing=None)


class SearchPageBrowsingModuleSchema(BasePostIdentifiersListModuleSchema):
    """Schema for search page browsing"""

    name = fields.Str()
    stop_css_selector = fields.Str(default=None, missing=None)
    listing_container_css_selector = fields.Str(default=None, missing=None)
    hover_over_listing_elements = fields.Boolean(missing=False)
    scroll_down_after_get_new_page = fields.Boolean(default=False, missing=False)
    take_screenshots = fields.Boolean(default=False, missing=False)
    max_posts_to_browse = fields.Integer(default=None, missing=None)
    post_url_template = fields.Str(missing=None)
    # using longer delays by default, searching is important
    loading_delay = fields.Float(default=DEFAULT_REQUIRED_LOADING_DELAY, missing=DEFAULT_REQUIRED_LOADING_DELAY)
    loading_timeout = fields.Float(default=DEFAULT_REQUIRED_LOADING_TIMEOUT, missing=DEFAULT_REQUIRED_LOADING_TIMEOUT)
    action_before_search_pages_browsing_module: List[RequiredIdentifierRetrieverModuleSchema] = fields.List(
        fields.Nested(RequiredIdentifierRetrieverModuleSchema), missing=None
    )
    search_page_urls_builder_module: SearchPageURLBuilderModuleSchema = fields.Nested(
        SearchPageURLBuilderModuleSchema(), missing=None
    )
    post_identifiers_retriever_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )
    poster_post_identifiers_retriever_module: PosterPostRetreivalModuleSchema = fields.Nested(
        PosterPostRetreivalModuleSchema(), missing=None
    )
    load_more_results_module: RequiredIdentifierRetrieverModuleSchema = fields.Nested(
        RequiredIdentifierRetrieverModuleSchema(), missing=None
    )

    description_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    price_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    vendor_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    poster_link_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )


class PostInformationRetrieverModuleSchema(BasePostIdentifiersListModuleSchema):
    """Schema for post listing retrieval"""

    name = fields.Str()
    post_url_template = fields.Str(missing=None)
    endpoint_post_url_template = fields.Str(missing=None)
    record_redirection_url = fields.Boolean(default=True, missing=True)
    loading_delay = fields.Float(default=DEFAULT_LOADING_DELAY, missing=DEFAULT_LOADING_DELAY)
    loading_timeout = fields.Float(default=DEFAULT_LOADING_TIMEOUT, missing=DEFAULT_LOADING_TIMEOUT)
    take_screenshot = fields.Boolean(default=True, missing=True)
    action_before_retrieving_post_information_module: List[IdentifierRetrieverModuleSchema] = fields.List(
        fields.Nested(IdentifierRetrieverModuleSchema), missing=None
    )

    post_url_cleaning_module: UrlCleaningSchema = fields.Nested(UrlCleaningSchema(), missing=None)

    driver_initialization_module: DriverInitializationModuleSchema = fields.Nested(
        DriverInitializationModuleSchema(), missing=None
    )


class PosterInformationRetrieverModuleSchema(CustomSchema):
    """Schema for post information retrieval"""

    name = fields.Str()
    poster_url_template = fields.Str()
    poster_url_replace_old_regex = fields.Str(default=None, missing=None)
    poster_url_replace_new = fields.Str(default=None, missing=None)
    record_redirection_url = fields.Boolean(default=True, missing=True)
    skip_query_string_cleaning = fields.Boolean(default=False, missing=False)
    loading_delay = fields.Float(default=DEFAULT_LOADING_DELAY, missing=DEFAULT_LOADING_DELAY)
    loading_timeout = fields.Float(default=DEFAULT_LOADING_TIMEOUT, missing=DEFAULT_LOADING_TIMEOUT)
    take_screenshot = fields.Boolean(default=True, missing=True)

    switch_to_iframe: IdentifierRetrieverModuleSchema = fields.Nested(IdentifierRetrieverModuleSchema(), missing=None)

    action_before_retrieving_post_information_module: List[IdentifierRetrieverModuleSchema] = fields.List(
        fields.Nested(IdentifierRetrieverModuleSchema), missing=None
    )
    poster_name_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    description_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    picture_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )
    payload_retriever_module: IdentifierRetrieverModuleSchema = fields.Nested(
        IdentifierRetrieverModuleSchema(), missing=None
    )


class LoginModule(CustomSchema):
    """Schema for login module"""

    login_page_url = fields.String()
    cookies_css_selector = fields.String(default=None, missing=None)
    username_css_selector = fields.String()
    password_css_selector = fields.String()
    submit_css_selector = fields.String()
    username = fields.String()
    password = fields.String()


class ArchivingSchema(CustomSchema):
    """Schema for archiving information retrieval"""

    sleep_after_get = fields.Integer(default=DEFAULT_SLEEP_AFTER_GET, missing=DEFAULT_SLEEP_AFTER_GET)
    remove_elements = fields.List(fields.Str(), missing=[])

    click_on_elements = fields.List(fields.Str(), missing=[])

    scroll_to_bottom = fields.Boolean(default=False, missing=False)

    scroll_sleep = fields.Integer(default=DEFAULT_SCROLL_SLEEP, missing=DEFAULT_SCROLL_SLEEP)
    sleep_after_operations = fields.Integer(
        default=DEFAULT_SLEEP_AFTER_OPERATIONS, missing=DEFAULT_SLEEP_AFTER_OPERATIONS
    )
    width = fields.Integer(missing=None)
    height = fields.Integer(missing=None)


class ProxySchema(CustomSchema):
    name = fields.Str(missing=None)
    country = fields.Str(missing=None)


class ScrapeSchema(CustomSchema):
    """Scraper Config Schema"""

    name = fields.Str()
    post_identifier_regex = fields.Str()
    driver_initialization_module: DriverInitializationModuleSchema = fields.Nested(
        DriverInitializationModuleSchema(), missing=None
    )
    search_pages_browsing_module: SearchPageBrowsingModuleSchema = fields.Nested(
        SearchPageBrowsingModuleSchema(), missing=None
    )
    post_information_retriever_module: PostInformationRetrieverModuleSchema = fields.Nested(
        PostInformationRetrieverModuleSchema(), missing=None
    )
    poster_information_retriever_module: PosterInformationRetrieverModuleSchema = fields.Nested(
        PosterInformationRetrieverModuleSchema(), missing=None
    )
    login_module: LoginModule = fields.Nested(LoginModule(), missing=None)

    post_url_cleaning_module: UrlCleaningSchema = fields.Nested(UrlCleaningSchema(), missing=None)
    poster_url_cleaning_module: UrlCleaningSchema = fields.Nested(UrlCleaningSchema(), missing=None)

    archiving_options: ArchivingSchema = fields.Nested(ArchivingSchema(), missing=None)

    proxies: List[ProxySchema] = fields.List(fields.Nested(ProxySchema), missing=None)
