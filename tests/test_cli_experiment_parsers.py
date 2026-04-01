from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_cli_sensitivity_experiment import (
    DIMENSION_IDS,
    parse_bad_summaries,
    parse_good_summaries,
)

GOOD_FILE = Path('/Users/samuel/Desktop/LENS Project/MTS-Dialog-ValidationSet_top10_longest_section_texts.txt')
BAD_FILE = Path('/Users/samuel/Desktop/LENS Project/lens_bad_samples_complete_english.txt')


@pytest.fixture(scope='module')
def good_samples():
    if not GOOD_FILE.exists():
        pytest.skip(f'Missing good sample file: {GOOD_FILE}')
    return parse_good_summaries(GOOD_FILE)


@pytest.fixture(scope='module')
def bad_samples():
    if not BAD_FILE.exists():
        pytest.skip(f'Missing bad sample file: {BAD_FILE}')
    return parse_bad_summaries(BAD_FILE)


def test_good_parser_returns_10_summaries(good_samples):
    assert len(good_samples) == 10


def test_bad_parser_returns_10_summaries(bad_samples):
    assert len(bad_samples) == 10


def test_ids_match(good_samples, bad_samples):
    good_ids = {sample.source_id for sample in good_samples}
    bad_ids = {sample.source_id for sample in bad_samples}
    assert good_ids == bad_ids


def test_expected_low_scoring_dimensions_extraction_works(bad_samples):
    sample_by_id = {sample.source_id: sample for sample in bad_samples}
    sample_14 = sample_by_id['14']
    assert sample_14.expected_low_scoring_dimensions == [
        'factual_accuracy',
        'relevant_chronic_problem_coverage',
        'timeline_evolution',
        'recent_changes_highlighted',
        'usefulness_for_decision_making',
        'clarity_readability_formatting',
    ]
    for sample in bad_samples:
        assert sample.bad_summary_text
        assert set(sample.expected_low_scoring_dimensions).issubset(set(DIMENSION_IDS))
