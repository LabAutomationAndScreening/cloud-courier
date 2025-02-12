import os


def test_blah():
    assert os.environ["AWS_PROFILE"] == "localstack"
