Setup AWS Organization
======================
.. _setup-aws:

If you already have a AWS organization for your company, and are using AWS Identity Center, you can skip this.

#. Create an AWS account. This will be the "management" account of your organization, so use a generic company email address (not your own). You'll likely need the company credit card to put on file during this setup. TODO: add more details
#. `Turn that account into an AWS Organization <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_create.html>`_
#. Note down the AWS Organization ID. You'll need this later. (e.g. ``o-2v54b6ap2r``)
#. Enable AWS Identity Center, and note down the application ID (e.g. ``d-9067c20053``)
#. Within Identity Center, go to Settings->Authentication->Send Email to users created by API (there’s no programmatic way to do this as of 2/5/25) if you are not using an External Identity Provider (and are creating users directly through the API)
#. Create the Github Repository that will manage your AWS Organization.
    #. In your Github organization, click Create New Repository. Name it something like ``aws-organization``
    #. Follow the steps in `the AWS Organization template repository <https://github.com/LabAutomationAndScreening/copier-aws-organization>`_ to set up your own repsoitory.
    #. Do not merge the code to the ``main`` branch yet. You'll need to deploy the Pulumi Bootstrap Cloudformation Stack first
#. Deploy the Pulumi Bootstrap Cloudformation Stack
    #. Find the file within your AWS Organization repository called ``pulumi-bootstrap.yaml`` and download it.
    #. Go to the AWS Cloudformation Console, and click Create Stack.
    #. TODO: add more detailed instructions on deploying the stack
#. Merge the code to the ``main`` branch of your Github repository (TODO: add more details on how to do this). This will trigger the initial creation of various baseline AWS accounts and resources.
#. Create the Github Repository that will manage your Central Infrastructure (including users and permissions).
    #. In your Github organization, click Create New Repository. Use the name you provided in the questionnaire when instantiating the ``aws-organization`` code from the template (typically ``aws-central-infrastructure``)
    #. Follow the steps in `the AWS Central Infrastructure template repository <https://github.com/LabAutomationAndScreening/copier-aws-central-infrastructure>`_ to set up your own repsoitory. (make sure to say initial deploy of IaC stack has not occurred yet)
    #. Merge the code to main to initially deploy the key portions of it.
    #. Create a new feature branch and update the questionnaire to say that IaC has been deployed.
    #. Merge the code to main to complete the initial deployment.
