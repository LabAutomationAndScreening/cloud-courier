Setup AWS Organization
======================
.. _setup-aws:

If you already have a AWS organization for your company, and are using AWS Identity Center, you can skip this.

#. `Create an AWS account <https://signin.aws.amazon.com/signup?request_type=register>`_. This will be the "management" account of your organization, so use a generic company email address (not your own...but if you need to use your own for now, it can be changed later). You'll likely need the company credit card to put on file during this setup. TODO: add more details
#. `Turn that account into an AWS Organization <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_create.html>`_
#. Note down the AWS Organization ID (e.g. ``o-2v54b6ap2r``) and the Account ID of the management account (e.g. ``123456789012``); you'll need these later.
#. Enable AWS Identity Center by navigating `here <https://console.aws.amazon.com/singlesignon>`_ and clicking ``Enable``. Then note down the application ID (e.g. ``d-9067c20053``) listed as part of the ``AWS access portal URL``.
#. Within Identity Center, go to Settings->Authentication. Click Configure on the Standard Authentication section, check the ``Send email OTP`` box and click Save (there's no programmatic way to do this as of 2/5/25) if you are not using an External Identity Provider (and are creating users directly through the API).
#. Create the Github Repository that will manage your AWS Organization.
    #. In your Github organization, click Create New Repository. Name it something like ``aws-organization``
    #. Follow the steps in `the AWS Organization template repository <https://github.com/LabAutomationAndScreening/copier-aws-organization>`_ to set up your own repository.
    #. Do not merge the code to the ``main`` branch yet. You'll need to deploy the Pulumi Bootstrap Cloudformation Stack first
#. Deploy the Pulumi Bootstrap Cloudformation Stack
    #. Find the file within your AWS Organization repository called ``pulumi-bootstrap.yaml`` and download it.
    #. Go to the `AWS Cloudformation Console <https://console.aws.amazon.com/cloudformation>`_, and click Create Stack.
    #. Under "Specify Template", choose "Upload a template file", and upload the ``pulumi-bootstrap.yaml`` file. Then click "Next".
    #. You should now be at "Step 2: Specify Stack Details". Enter something descriptive for the Stack Name (e.g. ``pulumi-bootstrap``), fill in your AWS Organization ID, and the GitHub repository name you created to manage your AWS Organization. Click "Next".
    #. You should now be at "Step 3: Configure Stack Options". Scroll to the bottom and check "I acknowledge that AWS CloudFormation might create IAM resources with custom names." then click "Next".
    #. You should now be at "Step 4: Review and create". Scroll to the bottom and click "Submit".
    #. You should now see a Stack Info tab with the Status of "CREATE_IN_PROGRESS". Wait for it to change to "CREATE_COMPLETE" before proceeding.
#. Merge the code to the ``main`` branch of your Github repository (TODO: add more details on how to do this). This will trigger the initial creation of various baseline AWS accounts and resources.
#. Create the Github Repository that will manage your Central Infrastructure (including users and permissions).
    #. In your Github organization, click Create New Repository. Use the name you provided in the questionnaire when instantiating the ``aws-organization`` code from the template (typically ``aws-central-infrastructure``)
    #. Follow the steps in `the AWS Central Infrastructure template repository <https://github.com/LabAutomationAndScreening/copier-aws-central-infrastructure>`_ to set up your own repository. (make sure to say initial deploy of IaC stack has not occurred yet)
    #. Merge the code to main to initially deploy the key portions of it.
    #. Create a new feature branch and update the questionnaire to say that IaC has been deployed.
    #. Merge the code to main to complete the initial deployment.
