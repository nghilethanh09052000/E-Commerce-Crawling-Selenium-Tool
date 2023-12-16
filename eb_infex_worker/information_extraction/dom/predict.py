import logging
from typing import Dict

import numpy as np
import sklearn.metrics
from sklearn.metrics import average_precision_score

log = logging.getLogger(__name__)


def evaluation_perf(uniq_row_ids, row_ids, scores, gts) -> Dict:
    """
    Compute DOM node prediction perf (grouped per website)
    """
    aps = []
    good_preds = []
    for row_id in uniq_row_ids:
        row_gt = gts[row_ids == row_id]
        row_score = scores[row_ids == row_id]
        if row_gt.any():
            ap = average_precision_score(row_gt, row_score)
            good_pred = np.argmax(row_gt) == np.argmax(row_score)
        else:
            ap, good_pred = 0, 0
        aps.append(ap)
        good_preds.append(good_pred)
    acc = np.mean(good_preds)
    macro_ap = np.mean(aps)
    micro_ap = average_precision_score(gts, scores)

    pred = scores > 0.5
    node_prec = sklearn.metrics.precision_score(gts, pred, zero_division=0)
    node_rec = sklearn.metrics.recall_score(gts, pred)
    return {
        "acc": acc,  # accurately predicted DOM node per each website
        "macro_ap": macro_ap,  # avg AP per each website
        "micro_ap": micro_ap,  # global AP over all websites
        "node_prec": node_prec,  # Node levl precision
        "node_rec": node_rec,
    }  # Node level recall


def perfstring(p):
    return "A: {:.2f} M: {:.2f} m: {:.2f}".format(p["acc"] * 100, p["macro_ap"] * 100, p["micro_ap"] * 100)


def compute_print_perf(Y, rids, proba, print_label):
    p = evaluation_perf(rids.unique(), rids, proba, Y)
    if print_label:
        # precision/recall on the level of websites
        log.info("(Website) {}: {}".format(print_label, perfstring(p)))
        # precious/recall over all nodes
        log.debug("(Node) {}: prec: {:.2f} rec: {:.2f}".format(print_label, p["node_prec"] * 100, p["node_rec"] * 100))
    return p
