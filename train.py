import json
import random

import click
import spacy
from spacy.util import compounding
from spacy.util import minibatch


@click.command()
@click.option(
    "--iterations",
    type=int,
    default=20,
    help="Number of training iterations (default 20)",
)
@click.option("--drop", type=float, default=0.2, help="Default 0.2")
@click.option(
    "--input-model",
    default="en_core_web_sm",
    help="Name of starting model (default en_core_web_sm)",
)
@click.option(
    "--output-model",
    type=click.Path(exists=False),
    required=True,
    help="Name of output model (directory)",
)
@click.option(
    "--enable-existing-ner/--disable-existing-ner",
    is_flag=True,
    default=False,
    help="Use an existing NER in the input model.  Default is DO NOT.",
)
@click.option("--tok2vec", type=click.File("rb"))
@click.option("--verbose", is_flag=True, default=False)
@click.argument("training_file", type=click.File("r"), nargs=-1)
def main(
    training_file,
    input_model,
    output_model,
    enable_existing_ner,
    iterations,
    drop,
    tok2vec,
    verbose,
):
    """
    Create an model to recognize named entities from 1 or more TRAINING_FILEs.
    """

    training_data = []

    for data_file in training_file:
        data = json.load(data_file)
        for entry in data:
            training_data.append(entry)

    if verbose:
        print("Loaded {} entries".format(len(training_data)))

    kwargs = dict()
    if not enable_existing_ner:
        kwargs["disable"] = "ner"

    nlp = spacy.load(input_model, **kwargs)
    if "ner" not in nlp.pipe_names:
        ner = nlp.create_pipe("ner")
        nlp.add_pipe(ner, last=True)
    else:
        ner = nlp.get_pipe("ner")
    ner.add_label("S-Component")
    pipe_exceptions = ["trf_tok2vec", "ner"]
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe not in pipe_exceptions]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        if tok2vec is not None:
            ner.model.tok2vec.from_bytes(tok2vec.read())
            tok2vec.close()
        batch_sizes = compounding(4.0, 32.0, 1.001)
        for itn in range(iterations):
            losses = {}
            random.shuffle(training_data)
            batches = minibatch(training_data, size=batch_sizes)
            for batch in batches:
                text, annotations = zip(*batch)
                nlp.update(text, annotations, drop=drop, sgd=optimizer, losses=losses)
            print("Iteration {}: {}".format(itn, losses))

    nlp.to_disk(output_model)


if __name__ == "__main__":
    main()
