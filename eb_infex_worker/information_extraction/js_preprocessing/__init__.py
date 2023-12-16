from pathlib import Path


def read_script(path):
    with open(path, "r") as f:
        return f.read()


def get_main_script():
    fold = Path(__file__).parent
    scripts = [
        fold / "bom/bomlib.js",
        fold / "bom/md5.js",
        fold / "bom/polyk.js",
        fold / "bom/rectlib.js",
        fold / "jquery-3.4.1.min.js",
        fold / "main.js",
    ]

    script = ""
    for path in scripts:
        script += read_script(path) + "\n"

    return script


def old_get_main_script():
    fold = Path(__file__).parent
    scripts = [
        fold / "bom/bomlib.js",
        fold / "bom/md5.js",
        fold / "bom/polyk.js",
        fold / "bom/rectlib.js",
        fold / "jquery-3.4.1.min.js",
        fold / "old_main.js",
    ]

    script = ""
    for path in scripts:
        script += read_script(path) + "\n"

    return script
