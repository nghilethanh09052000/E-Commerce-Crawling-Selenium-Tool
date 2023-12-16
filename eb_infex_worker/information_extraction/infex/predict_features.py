import numpy as np
from eb_infex_worker.information_extraction.infex.predict_nodes_lxml import (
    convert_lxml_tree_to_features_price,
    convert_lxml_tree_to_features_title,
)


def predict_features(tree, price_clf, price_scaler, title_clf, title_scaler):

    title_features, title_insights = convert_lxml_tree_to_features_title(tree, 0)
    title_np_features = []
    for feats in title_features:
        nfeats = np.hstack([np.array(x) for x in feats.values()])
        title_np_features.append(nfeats)

    if len(title_np_features) > 0:
        title_np_features = np.vstack(title_np_features)

        x = title_np_features[:, 2:]

        x = title_scaler.transform(x)
        preds = title_clf.predict_proba(x)[:, 1]
        title = title_insights[np.argmax(preds)]["node_text_content"]
    else:
        title = None

    price_features, price_insights = convert_lxml_tree_to_features_price(tree, 0)
    price_np_features = []
    for feats in price_features:
        nfeats = np.hstack([np.array(x) for x in feats.values()])
        price_np_features.append(nfeats)

    if len(price_np_features) > 0:
        price_np_features = np.vstack(price_np_features)

        x = price_np_features[:, 2:]

        x = price_scaler.transform(x)
        preds = price_clf.predict_proba(x)[:, 1]
        price = price_insights[np.argmax(preds)]["node_text_content"]
    else:
        price = None

    return title, price
