# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from enum import StrEnum


class ApplicationBootupModes(StrEnum):
    EXE = "exe"
    DOCKER_COMPOSE = "docker-compose"


BACKEND_PORT = 4000
APPLICATION_BOOTUP_MODE: ApplicationBootupModes = ApplicationBootupModes.EXE
APP_NAME = "cloud-courier"  # for executables, this should match what's used in pyinstaller.spec, but containerized apps it is currently not utilized
