#
# method
# - read in multiple JSON-L format SSP files
# - collate by controls
# - for each control:
#   - construct spacy doc for each SSP's statement
#   - compute similarity measure
#   - build a graph showing which control statements are related
# assumptions:
# - all controls come from same catalog
# - only one instance of a control per SSP (this should
#   be true, but it sometimes is not!
import json
import textwrap
from collections import defaultdict

import click
import spacy
from graph import Graph


def add_controls(controls, tag, ssp_path):
    with open(ssp_path, "r") as ssp_file:
        for line in ssp_file:
            statement = json.loads(line)
            control_key = statement["control"]
            text = statement["text"]
            controls[control_key].append((tag, text))


def similarity_controls(nlp, controls, threshold):
    components = {}
    for control_key in controls:
        components[control_key] = similarity_by_statement(
            nlp, controls[control_key], threshold
        )
    return components


def similarity_controls_sentences(nlp, controls, threshold):
    components = {}
    for control_key in controls:
        components[control_key] = similarity_by_sentence(
            nlp, controls[control_key], threshold
        )
    return components


def similarity_by_sentence(nlp, statements, threshold):
    docs = [nlp(text) for _, text in statements]
    tags = [tag for tag, _ in statements]

    s_docs = []
    s_tags = []

    for tag, doc in zip(tags, docs):
        for idx, sent in enumerate(doc.sents):
            s_tag = f"{tag}_{idx}"
            s_doc = nlp(sent.text)
            s_tags.append(s_tag)
            s_docs.append(s_doc)

    return similarity(s_tags, s_docs, threshold)


def similarity_by_statement(nlp, statements, threshold):
    docs = [nlp(text) for _, text in statements]
    tags = [tag for tag, _ in statements]

    return similarity(tags, docs, threshold)


def similarity(tags, docs, threshold):
    docs_by_tag = {tag: doc for tag, doc in zip(tags, docs)}

    matrix = [
        [0.0 if doc1 == doc2 else doc1.similarity(doc2) for doc2 in docs]
        for doc1 in docs
    ]

    g = Graph()

    for tag, doc in zip(tags, docs):
        g.add_node(tag, doc)

    for row_tag, row in zip(tags, matrix):
        for col_tag, sim in zip(tags, row):
            if sim >= threshold:
                g.add_edge(row_tag, col_tag, sim)

    return (g.components(), docs_by_tag)


def display(components):
    for control in sorted(components):
        print(f"Control {control}")
        docs_by_tag = components[control][1]
        for match in components[control][0]:
            sorted_matches = sorted(match)
            print("  [" + ", ".join(sorted_matches) + "]")
            for tag in sorted_matches:
                print(
                    f"    {tag}:",
                    textwrap.shorten(
                        str(docs_by_tag[tag]), width=72, placeholder="..."
                    ),
                )
        print()


@click.command()
@click.option("--ssp", type=(str, click.Path(exists=True)), multiple=True)
@click.option("--threshold", type=float, default=0.95)
@click.option("--by", type=click.Choice(["statement", "sentence"]), default="statement")
def main(ssp, by, threshold):
    controls = defaultdict(list)
    tags = set()
    for tag, ssp_path in ssp:
        if tag in tags:
            raise click.ClickException("duplicate SSP tag {}".format(tag))
        tags.add(tag)
        add_controls(controls, tag, ssp_path)

    nlp = spacy.load("en_core_web_lg")

    if by == "statement":
        print("# Similarity by control statement\n")
        display(similarity_controls(nlp, controls, threshold))
    elif by == "sentence":
        print("\n# Similarity by sentence\n")
        display(similarity_controls_sentences(nlp, controls, threshold))


if __name__ == "__main__":
    main()
