/* Check that the node is well defined (for dom, geo, log nodes)*/
function is_node(node) {
    return (typeof node !== "undefined" && node !== null)
}


/* Get the parent node (for dom, geo, log nodes) */
function get_parent(node) {
    if (is_node(node.parent)) {
        return node.parent;
    }
    return node.parentNode;
}


/* Check if the node is a leaf (has no valid children) */
function is_leaf(node) {
    var leaf = true;
    for (var i = 0; i < node.children.length; i++) {
        if (is_node(node.children[i])) {
            leaf = false;
        }
    }
    return leaf;
}


/* List the parents of the given node */
function list_parents(node) {
    var parents = [];
    while (is_node(node)) {
        parents.push(node);
        node = get_parent(node)
    }
    return parents;
}


/* Find the common ancestor to a list of nodes */
function common_ancestor(nodes) {
    var node_1 = nodes.pop();
    if (nodes.length == 0) {
        return node_1;
    }
    var node_2 = nodes.pop();

    var parents = list_parents(node_2);
    var i = parents.indexOf(node_1);
    while (i == -1 && is_node(node_1)) {
        node_1 = get_parent(node_1);
        i = parents.indexOf(node_1);
    }

    if (i != -1) {
        ancestor = parents[i];
        nodes.push(ancestor);
        return common_ancestor(nodes)
    }
    return undefined
}


/* Get the geo root nodes belonging to a list of log nodes */
function get_geo_nodes(log_nodes) {
    var geo_nodes = [];
    for (var i = 0; i < log_nodes.length; i++) {
        var log = log_nodes[i];
        if (!is_node(log)) {
            continue;
        }
        for (var j = 0; j < log.geometricObjects.length; j++) {
            var geo = log.geometricObjects[j];
            if (is_node(geo)) {
                geo_nodes.push(geo)
            }
        }
    }

    return geo_nodes;
}


/* Find nodes that validate a condition through depth first search */
function tree_depth_search(current_node, cond_func, valid_nodes) {
    if (typeof valid_nodes === "undefined") {
        valid_nodes = []
    }

    if (typeof cond_func === "undefined") {
        function _always_true(node) {
            return true;
        }
        cond_func = _always_true
    }

    if (cond_func(current_node)) {
        valid_nodes.push(current_node)
    }

    for (var i = 0; i < current_node.children.length; i++) {
        var child = current_node.children[i];
        if (!is_node(child)) {
            continue
        }
        valid_nodes = tree_depth_search(child, cond_func, valid_nodes)
    }

    return valid_nodes
}


/* Find the root geo node that is the logical parent of the element
 * First find the logical nodes containing the element in the log tree
 * Then merge their geo nodes, and find their common ancestor
 */
function get_segment_nodes(log_root, element) {
    var parents = list_parents(element);

    // valid = leaf log node + contains an ancestor of the element
    function is_valid(log) {
        if (!is_leaf(log)) {
            return false;
        }
        for (var i = 0; i < log.geometricObjects.length; i++) {
            var geo = log.geometricObjects[i];
            if (parents.indexOf(geo.element) != -1) {
                return true;
            }
        }
        return false;
    }
    var log_nodes = tree_depth_search(log_root, is_valid);
    var geo_nodes = get_geo_nodes(log_nodes);
    return geo_nodes
}

/* Enrich an element from geo node 
 * If no element is provided, enrich the element of the geo node
 */
function enrich(element) {
    // getPropertyValue does no work well, JSON.stringify(css) is too heavy
    css = window.getComputedStyle(element);

    element.setAttribute("data-nv-reachable", true);
    element.setAttribute("data-nv-visible", css.display !== "none");
    good_elements = ["backgroundColor", "color", "display", "fontFamily",
        "fontSize", "fontStyle", "fontWeight", "justifyContent", "textAlign",
        "textDecorationLine", "textTransform"]
    good_css = {}
    for (el of good_elements) {
        element.setAttribute("data-nv-css-"+el, css[el])
    }

    rect = element.getBoundingClientRect();
    element.setAttribute("data-nv-x", rect.x);
    element.setAttribute("data-nv-y", rect.y);
    element.setAttribute("data-nv-w", rect.width);
    element.setAttribute("data-nv-h", rect.height);
    return false;
}


/* Clean dom tree, keeping only main_element in the body */
function clean_dom(document, geo_nodes) {
    var body = document.body;

    while (body.firstChild) {
        body.removeChild(body.lastChild);
    }

    for (i = 0; i < geo_nodes.length; i++) {
        body.appendChild(geo_nodes[i].element);
      }
}


/* Get the element given its xpath */
function get_element_by_xpath(path) {
    return document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}

/* Add data to all nodes/tags */
function enrich_all() {
    var all = document.getElementsByTagName("*");
    for (var i=0, max=all.length; i < max; i++) {
         enrich(all[i])
    }
}

/* Remove comments from DOM tree */
function remove_comments() {
    $('*').contents().each(function() {
        if(this.nodeType === Node.COMMENT_NODE) {
            $(this).remove();
        }
    });
}

/* Remove scripts and head tags */
function remove_script_head() {
    $('script').remove();
    $('head').remove();
}

/* Merge all node with only 1 child */
function merge_single_child(el) {
    let parent = el.parent();
    let children = el.children();

    if (children.length == 1 && !el.clone().children().remove().end().text().trim() && parent.length > 0) {

        for (let j=0, max=el[0].attributes.length; j < max; j++) {
            /* merge attributes of parent and child */
            let attribute_name = el[0].attributes[j].name;
            let attribute_value = el[0].attributes[j].value;

            if (attribute_name === "data-nv-flavour") {
                new_attribute_value = attribute_value;
            } else if (attribute_name.startsWith('data-nv') || attribute_name === "bomtype") {
                continue;
            } else if (children[0].getAttribute(attribute_name)) {
                new_attribute_value = attribute_value.concat(' ', children[0].getAttribute(attribute_name));
            } else {
                new_attribute_value = attribute_value;
            }
            try {
                children[0].setAttribute(attribute_name, new_attribute_value);
            } catch (error) {
                console.log("error setting attribute")
                console.error(error);
              }
        }

        el[0].replaceWith(children[0]);
    }

    for (var i=0, max=children.length; i < max; i++) {
        let child = $(children[i]);
        merge_single_child(child);
    }
}


function get_serialized_document() {
    return new XMLSerializer().serializeToString(document);
}


function task_page_preprocessing(do_segment, do_merge, x_path_image, pac, pdc) {
    if (do_segment) {
        if (typeof pac === "undefined") { pac = 5; }
        if (typeof pdc === "undefined") { pdc = 50; }
        var element = get_element_by_xpath(x_path_image);
        if (!is_node(element)) {
            // Can't do anything. should raise ? or at least not happen in here ?
            console.log("Cannot find the element with the given x_path:");
            console.log(x_path_image);
            console.log("Return None");
            return;
        }
        startSegmentation(window, pac, pdc);

        // Get the ancestor, fix the dom tree and add meta info
        console.log("Get Segment Nodes");
        var geo_nodes = get_segment_nodes(page, element);
    }

    // Enrich all nodes
    console.log("Enrich Each Node");
    enrich_all();

    if (do_segment) {
        // Delete all except relevant subtree
        console.log("Clean DOM With Segments Only");
        clean_dom(document, geo_nodes);
    }

    // Remove irrelevant tags
    console.log("Remove Irrelevant Tags");
    remove_comments();
    remove_script_head();

    if (do_merge) {
        // Merge single children
        console.log("Merge Single Children");
        merge_single_child($(document.documentElement));
    }

    // Return Serialized Document
    console.log("Return Serialized Document")
    return get_serialized_document();
}
