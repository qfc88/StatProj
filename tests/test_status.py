"""The status command must run and give sensible next steps."""

from src import status


def test_status_runs_for_a_member_and_for_the_team(capsys):
    status.main("Jovie")
    status.main(None)
    output = capsys.readouterr().out
    assert "Pending / next steps" in output
    assert "Jovie" in output


def test_unknown_name_is_reported(capsys):
    status.main("Nobody")
    assert "is not in docs/team/README.md" in capsys.readouterr().out


def test_counts_that_differ_make_galvin_stop():
    done = dict.fromkeys(status.PARTS, True)
    real = {"train_trips": 3500, "test_trips": 893, "modelling_rows": 3470, "fingerprint_ok": False}
    steps = status.pending_items(done, real)
    assert steps["galvin"][0].startswith("STOP")


def test_correct_counts_unblock_the_next_steps():
    done = dict.fromkeys(status.PARTS, True)
    real = {"train_trips": 3516, "test_trips": 877, "modelling_rows": 3484, "fingerprint_ok": True}
    steps = status.pending_items(done, real)
    assert steps["galvin"][0].startswith("Done")
    assert "python -m src.validation" in steps["anthony"][0]
