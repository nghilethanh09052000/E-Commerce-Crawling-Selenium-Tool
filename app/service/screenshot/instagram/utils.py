import base64
import re
from datetime import datetime
from urllib.request import urlopen

# Regex to retrieve words starting with # (Instagram hashtags) or @ (Instagram mentions)
REFERENCES_PATTERN = re.compile(r"(#\w+|@\w+)")
NOW = datetime.now()


def get_as_base64(url):
    """Convert an image URL to its base 64 representation"""

    b64_url = base64.b64encode(urlopen(url).read()).decode("utf-8")

    return f"data:image/jpeg;base64,{b64_url}"


def format_date(publication_datetime):
    """Format a datetime object with a format used by Instagram (e.g. July 15, 2021)"""

    return publication_datetime.strftime("%B %d, %Y")


def time_ago(dt):
    """Build a string telling how long ago a caption/comment was published, in Instagram style (38s, 25m, 3h, 2d, 7w)"""

    delta = NOW - dt

    seconds, days = delta.seconds, delta.days

    if days < 0:
        return ""

    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif days < 1:
        return f"{seconds // 3600}h"
    elif days < 7:
        return f"{days}d"
    else:
        return f"{days // 7}w"


def big_count(count):
    """Build a string telling how many followers/posts/followings a user has, in Instagram style (6,425; 29.4k; 4.6m; 303m)

    Values are handled up to 10^10 - 1 (the maximum number of followers is a few hundred millions as of March 2022)
    """

    if count < 10**4:
        figures = f"{count:,}"
        suffix = ""
    else:
        if count < 10**5:
            figures = str(count / 10**3)[:4]
            suffix = "k"
        elif count < 10**6:
            figures = str(count / 10**3)[:3]
            suffix = "k"
        elif count < 10**7:
            figures = str(count / 10**6)[:4]
            suffix = "m"
        else:
            figures = str(count / 10**6)[:3]
            suffix = "m"

        # Eliminate 0s in strings such as "7.0k" then points in strings such as "7.k"
        if "." in figures:
            figures = figures.strip("0").strip(".")

    return figures + suffix


def format_caption(caption):
    """Format a the caption text from the Instagram API to a text which will be displayed appropriately in HTML"""

    caption = caption.replace("\n", "<br>")

    # Build a list of words starting with # (hashtags) or @ (mentions)
    words_to_reference = REFERENCES_PATTERN.findall(caption)

    # Display those words as links
    for word in words_to_reference:
        caption = caption.replace(word, f"<a>{word}</a>")

    return caption


def get_post_type(post):
    """Determine the type of post

    Returns:
    ========
    post_type: str
        carousel, clip, video or image
    """

    if len(post["pictures"]) > 1:
        return "carousel"
    elif post["is_video"]:
        if post["is_clip"]:
            return "clip"
        else:
            return "video"
    else:
        return "image"


def get_post_svg_icon(post):
    post_type = get_post_type(post)

    if post_type == "image":
        return None
    elif post_type == "carousel":
        return """
            <svg aria-label="Carousel" class="_8-yf5 " color="#ffffff" fill="#ffffff" height="22"
                role="img" viewBox="0 0 48 48" width="22">
                <path
                d="M34.8 29.7V11c0-2.9-2.3-5.2-5.2-5.2H11c-2.9 0-5.2 2.3-5.2 5.2v18.7c0 2.9 2.3 5.2 5.2 5.2h18.7c2.8-.1 5.1-2.4 5.1-5.2zM39.2 15v16.1c0 4.5-3.7 8.2-8.2 8.2H14.9c-.6 0-.9.7-.5 1.1 1 1.1 2.4 1.8 4.1 1.8h13.4c5.7 0 10.3-4.6 10.3-10.3V18.5c0-1.6-.7-3.1-1.8-4.1-.5-.4-1.2 0-1.2.6z">
                </path>
            </svg>
        """
    elif post_type == "clip":
        return """
            <svg aria-label="Clip" class="_8-yf5 " color="#ffffff" fill="#ffffff" height="18" role="img"
                viewBox="0 0 24 24" width="18">
                <path
                d="M12.823 1l2.974 5.002h-5.58l-2.65-4.971c.206-.013.419-.022.642-.027L8.55 1zm2.327 0h.298c3.06 0 4.468.754 5.64 1.887a6.007 6.007 0 011.596 2.82l.07.295h-4.629L15.15 1zm-9.667.377L7.95 6.002H1.244a6.01 6.01 0 013.942-4.53zm9.735 12.834l-4.545-2.624a.909.909 0 00-1.356.668l-.008.12v5.248a.91.91 0 001.255.84l.109-.053 4.545-2.624a.909.909 0 00.1-1.507l-.1-.068-4.545-2.624zm-14.2-6.209h21.964l.015.36.003.189v6.899c0 3.061-.755 4.469-1.888 5.64-1.151 1.114-2.5 1.856-5.33 1.909l-.334.003H8.551c-3.06 0-4.467-.755-5.64-1.889-1.114-1.15-1.854-2.498-1.908-5.33L1 15.45V8.551l.003-.189z"
                fill-rule="evenodd"></path>
            </svg>
        """
    elif post_type == "video":
        return """
            <svg aria-label="Video" class="_8-yf5 " color="#ffffff" fill="#ffffff" height="18"
                role="img" viewBox="0 0 24 24" width="18">
                <path
                d="M5.888 22.5a3.46 3.46 0 01-1.721-.46l-.003-.002a3.451 3.451 0 01-1.72-2.982V4.943a3.445 3.445 0 015.163-2.987l12.226 7.059a3.444 3.444 0 01-.001 5.967l-12.22 7.056a3.462 3.462 0 01-1.724.462z">
                </path>
            </svg>
        """


def get_post_icon_div(post):
    post_svg_icon = get_post_svg_icon(post)

    if post_svg_icon:
        return f"""
            <div class="CzVzU">
                <div
                class="             qF0y9          Igw0E     IwRSH      eGOV_         _4EzTm    bkEs3                  soMvl                  JI_ht                  DhRcB                                                    ">

                {post_svg_icon}

                </div>
            </div>
        """
    else:
        return ""
