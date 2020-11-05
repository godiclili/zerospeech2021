"""Evaluation program for ZR2021 submissions"""

import atexit
import os
import pathlib
import shutil
import sys
import tempfile
import zipfile

import click
import yaml

from zerospeech2021 import phonetic, lexical, syntactic, semantic


def eval_lexical(dataset, submission, output, kinds):
    for kind in kinds:  # 'dev' or 'test'
        print(f'Evaluating lexical {kind}...')

        gold_file = dataset / 'lexical' / kind / 'gold.csv'
        submission_file = submission / 'lexical' / f'{kind}.txt'

        by_pair, by_frequency, by_length = lexical.evaluate(
            gold_file, submission_file)

        by_pair.to_csv(
            output / f'score_lexical_{kind}_by_pair.csv',
            index=False, float_format='%.4f')
        by_frequency.to_csv(
            output / f'score_lexical_{kind}_by_frequency.csv',
            index=False, float_format='%.4f')
        by_length.to_csv(
            output / f'score_lexical_{kind}_by_length.csv',
            index=False, float_format='%.4f')


def eval_semantic(dataset, submission, output, kinds):
    # load metric and poling parameters from meta.yaml
    meta = yaml.safe_load((submission / 'meta.yaml').open('r').read())
    metric = meta['parameters']['semantic']['metric']
    pooling = meta['parameters']['semantic']['pooling']

    for kind in kinds:  # 'dev' or 'test'
        print(f'Evaluating semantic {kind} '
              f'(metric={metric}, pooling={pooling})...')

        gold_file = dataset / 'semantic' / kind / 'gold.csv'
        pairs_file = dataset / 'semantic' / kind / 'pairs.csv'
        score = semantic.evaluate(
            gold_file, pairs_file, submission / 'semantic' / kind,
            metric, pooling)
        score.to_csv(
            output / f'score_semantic_{kind}.csv',
            index=False, float_format='%.4f')


def eval_syntactic(dataset, submission, output, kinds):
    for kind in kinds:  # 'dev' or 'test'
        print(f'Evaluating syntactic {kind}...')

        gold_file = dataset / 'syntactic' / kind / 'gold.csv'
        submission_file = submission / 'syntactic' / f'{kind}.txt'

        by_pair, by_type = syntactic.evaluate(gold_file, submission_file)
        by_pair.to_csv(
            output / f'score_syntactic_{kind}_by_pair.csv',
            index=False, float_format='%.4f')
        by_type.to_csv(
            output / f'score_syntactic_{kind}_by_type.csv',
            index=False, float_format='%.4f')


def eval_phonetic(dataset, submission, output, kinds):
    abx_data = dataset / 'phonetic' / 'abx_features'

    for kind in kinds:  # 'dev' or 'test'
        print(f'Evaluating phonetic {kind}...')

        features_location = submission / 'phonetic' / kind
        phonetic.evaluate(features_location, abx_data, output, kind)


@click.command(epilog='See https://zerospeech.com/2021 for more details')
@click.argument('dataset', type=pathlib.Path)
@click.argument('submission', type=pathlib.Path)
@click.option(
    '-o', '--output-directory', type=pathlib.Path,
    default='.', show_default=True,
    help="Directory to store output results")
@click.option('--no-phonetic', help="Skip phonetic part", is_flag=True)
@click.option('--no-lexical', help="Skip lexical part", is_flag=True)
@click.option('--no-syntactic', help="Skip syntactic part", is_flag=True)
@click.option('--no-semantic', help="Skip semantic part", is_flag=True)
def evaluate(
        dataset, submission, output_directory,
        no_phonetic, no_lexical, no_syntactic, no_semantic):
    """Evaluate a submission to the Zero Resource Speech Challenge 2021

    DATASET is the root directory of the ZR2021 dataset, as downloaded with the
    zerospeech2021-download tool.

    SUBMISSION is the submission to evaluate, it can be a .zip file or a
    directory.

    """
    try:
        # regular participants can only evaluate dev datasets, test can only be
        # evaluated by doing an official submission to the challenge. The
        # ZEROSPEECH2021_TEST_GOLD environment variable is used by organizers
        # to provide test gold files to the evaluation program while keeping
        # the program as simple as possible to participants.
        kinds = ['dev']
        if 'ZEROSPEECH2021_TEST_GOLD' in os.environ:
            kinds.append('test')
            dataset = pathlib.Path(os.environ['ZEROSPEECH2021_TEST_GOLD'])

        # ensures the dataset exists
        dataset = dataset.resolve(strict=True)
        if not dataset.is_dir():
            raise ValueError(f'dataset not found: {dataset}')

        # ensures the submission exists, it it is a zip, uncompress it
        submission = submission.resolve(strict=True)
        if submission.is_file() and zipfile.is_zipfile(submission):
            # create a temp directory we remove at exit
            submission_unzip = tempfile.mkdtemp()
            atexit.register(shutil.rmtree, submission_unzip)

            # uncompress to the temp directory
            print(f'Unzip submission ot {submission_unzip}...')
            zipfile.ZipFile(submission, 'r').extractall(submission_unzip)
            submission = submission_unzip
        elif not submission.is_dir():
            raise ValueError(
                f'submssion is not a zip file or a directory: {submission}')

        if not output_directory.is_dir():
            output_directory.mkdir(exist_ok=True, parents=True)

        if not no_lexical:
            eval_lexical(dataset, submission, output_directory, kinds)

        if not no_semantic:
            eval_semantic(dataset, submission, output_directory, kinds)

        if not no_syntactic:
            eval_syntactic(dataset, submission, output_directory, kinds)

        if not no_phonetic:
            eval_phonetic(dataset, submission, output_directory, kinds)
    except ValueError as error:
        print(f'ERROR: {error}')
        sys.exit(-1)