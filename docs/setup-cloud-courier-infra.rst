Setup Cloud Courier Infrastructure
==================================
.. _setup-cloud-courier-infra:

If you are not using the provided AWS Organization and Central Infrastructure templates, then use your own organization's mechanisms to provision AWS accounts for Cloud Courier (TODO: add more details).

#. Create the Github Repository that will manage your Cloud Courier installation.
    #. In your Github organization, click Create New Repository. Name it something like ``cloud-courier-infrastructure``
    #. Follow the steps in `the Cloud Courier Infrastructure template repository <https://github.com/LabAutomationAndScreening/copier-cloud-courier-infrastructure>`_ to set up your own repsoitory.
    #. Merge the code to ``main`` to deploy the initial infrastructure.
