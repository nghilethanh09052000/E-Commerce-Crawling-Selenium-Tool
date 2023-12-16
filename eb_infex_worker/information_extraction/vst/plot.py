import cv2
import numpy as np
import matplotlib.pyplot as plt
from contextlib import contextmanager
from typing import Optional, Iterable, List, Dict, Any, Union, Callable, TypeVar  # NOQA


def cv_put_box_with_text(
    image: np.ndarray,
    box_ltrd: Iterable[float],
    # Rectangle params
    rec_color=(255, 255, 255),  # White
    rec_thickness=4,
    # Text params
    text=None,
    text_size=0.6,
    text_color=None,
    text_thickness=2,
    text_position="left_down",
) -> np.ndarray:
    """
    Overwrites in place
    """

    l, t, r, d = map(int, box_ltrd)
    cv2.rectangle(image, (l, t), (r, d), color=rec_color, thickness=rec_thickness)

    fontFace = cv2.FONT_HERSHEY_SIMPLEX
    if text:
        if text_color is None:
            text_color = rec_color
        # Text Positioning

        retval, baseline = cv2.getTextSize(text, fontFace, text_size, text_thickness)
        if text_position == "left_down":
            text_pos = (l, d - 5)
        elif text_position == "left_up":
            text_pos = (l, t - 5)
        elif text_position == "right_down":
            text_pos = (r - retval[0], d - 5)
        elif text_position == "right_up":
            text_pos = (r - retval[0], t - 5)
        else:
            raise ValueError("Wrong text position")
        cv2.putText(
            image, text, text_pos, fontFace=fontFace, fontScale=text_size, color=text_color, thickness=text_thickness
        )
    return image


def cv_put_text(
    image, text, text_pos, text_size=0.6, text_color=(255, 255, 255), text_thickness=2, text_position="left_down"
):
    fontFace = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(
        image, text, text_pos, fontFace=fontFace, fontScale=text_size, color=text_color, thickness=text_thickness
    )


def plot_close(f, legend_list=[], impath=None):
    if impath:
        f.savefig(impath, bbox_extra_artists=legend_list, bbox_inches="tight")
    else:
        plt.show()
    plt.close(f)


@contextmanager
def plt_backend(backend_name):
    original = plt.get_backend()
    plt.switch_backend(backend_name)
    yield
    plt.switch_backend(original)
