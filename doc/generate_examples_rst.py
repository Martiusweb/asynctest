# coding: utf-8
import fnmatch
import pathlib
import os.path
import re
import logging

logging.basicConfig(level=logging.INFO)

INCLUDED_SOURCES = ("*.py", )
EXCLUDED_SOURCES = ("__*__.py", )

INCLUDED_SOURCES_REGEX = tuple(re.compile(fnmatch.translate(pattern))
                               for pattern in INCLUDED_SOURCES)

EXCLUDED_SOURCES_REGEX = tuple(re.compile(fnmatch.translate(pattern))
                               for pattern in EXCLUDED_SOURCES)


def include_file(filename):
    return (any(regex.match(filename) for regex in INCLUDED_SOURCES_REGEX) and
            not any(regex.match(filename) for regex in EXCLUDED_SOURCES_REGEX))


def list_examples(src_dir):
    examples = []
    for dirname, _, filenames in os.walk(src_dir):
        for filename in filenames:
            if include_file(filename):
                examples.append((pathlib.Path(dirname), filename))

    index_contents = []
    return sorted(examples)


def generate_examples_rst(src_dir="examples/"):
    examples = list_examples(src_dir)

    # Generate the index
    logging.info("Creating index file")
    with open(os.path.join(src_dir, "index.rst"), "w") as index:
        index.write(
            "List of code examples\n"
            "---------------------\n"
            "\n"
            ".. toctree::\n"
            "\n"
        )

        for example_dirname, example_filename in examples:
            example_pathname = os.path.join(
                example_dirname.relative_to(src_dir),
                example_filename)
            rst_filename = os.path.join(src_dir, f"{example_pathname}.rst")

            index.write(f"   {example_pathname}\n")

            logging.info("generating file for %s", example_pathname)
            with open(rst_filename, "w") as example_rst:
                example_rst.write(
                    f"``{example_pathname}``\n"
                    f"{'-' * (len(example_pathname) + 4)}\n\n"
                    f".. literalinclude:: {example_filename}\n"
                )

    logging.info("index and source file generated")


if __name__ == "__main__":
    generate_examples_rst()
