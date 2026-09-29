.. _installation:

Installation
============
How to set up Cloud Courier in your lab.

#. Set up a Github account and organization (if you don't have one). :doc:`Setup Github <setup-github>`.
#. Set up an Amazon Web Services Organization (if you don't have one). :doc:`Setup AWS Organization <setup-aws>`.
#. :doc:`Set up the Cloud Courier Infrastructure basics <setup-cloud-courier-infra>`.
#. Configure the permissions for the Cloud Courier administrators. TODO: add details
#. :doc:`Configure settings for Lab Computers <configure-lab-computers>`.
#. :doc:`Connect the lab computers to your AWS cloud <connect-computer-to-aws>`.
#. Initially install the Cloud Courier upload agent on the lab computers. TODO: add details

   .. TODO: document the MSI installer once it is genuinely installable. The nuxt template brought an MSI
      and a Windows service that this repo never had before, and both build in CI, but nothing yet supplies
      the agent with --aws-region or --stop-flag-dir, so a real install registers a service that fails on
      its first start. See the TODOs above _install_service in
      backend/tests/windows_service/test_service_lifecycle.py for the open questions. Until that is
      resolved, the manual setup described on this page and in configure-lab-computers is still how
      cloud-courier is deployed. When the MSI does work, cover the install itself, the service account and
      its rights, where logs and crash dumps land, and the upgrade path; note also that the MSI is unsigned,
      so operators will see a SmartScreen warning.
#. Configure the permissions for end users to access the data. TODO: add details
#. Install software on end user laptops to access the data. TODO: add details

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   setup-github
   setup-aws
   setup-cloud-courier-infra
   configure-lab-computers
   connect-computer-to-aws
