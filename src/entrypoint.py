import sys  # pragma: no cover # we can't unit test the entrypoint itself. It is tested in the E2E test of the executable

from cloud_courier.main import (
    entrypoint,
)  # pragma: no cover # we can't unit test the entrypoint itself. It is tested in the E2E test of the executable

if __name__ == "__main__":
    sys.exit(entrypoint(sys.argv[1:]))
