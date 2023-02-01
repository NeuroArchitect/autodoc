import logging
import os

import libcst.tool
import yaml

logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def main():
    logger.debug("running autodoc from %s" % os.getcwd())
    if not os.path.exists(os.path.join(os.getcwd(), libcst.tool.CONFIG_FILE_NAME)):
        logger.info("generating configuration file %s" % libcst.tool.CONFIG_FILE_NAME)
        libcst.tool.main("autodoc", ["initialize", os.getcwd()])

    logger.debug("reading configuration %s" % libcst.tool.CONFIG_FILE_NAME)
    with open(libcst.tool.CONFIG_FILE_NAME, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    if "autodoc.codemod" not in config["modules"]:
        config["modules"].append("autodocstr.codemod")
    with open(libcst.tool.CONFIG_FILE_NAME, "w") as f:
        yaml.dump(config, f)

    libcst.tool.main(
        "autodoc",
        [
            "codemod",
            "commands.AutodocWithCodexCommand",
            "--jobs",
            "1",
            os.getcwd(),
        ],
    )


if __name__ == "__main__":
    main()
