# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
APP_NAME = "cloud-courier"
DEPLOYED_PORT_NUMBER = 4000
HUMAN_FRIENDLY_APP_NAME = "Cloud Courier"
DEFAULT_DEPLOYED_HOST = "127.0.0.1"

# Windows service identity. The registered name is org-prefixed to avoid
# colliding with any other service already on the machine; kept separate from
# APP_NAME (which also names crash dumps, templates, etc.).
WINDOWS_SERVICE_NAME = f"LabAutomationAndScreening-{APP_NAME}"
WINDOWS_SERVICE_DISPLAY_NAME = f"Lab Automation and SCreening {HUMAN_FRIENDLY_APP_NAME}"
