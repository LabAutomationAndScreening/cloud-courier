Connect a Lab Computer to AWS
=============================
.. _connect-computer-to-aws:

This documents how to perform the one-time process to connect a lab computer to your Amazon Web Services cloud.

#. Navigate to your ``cloud-courier-infrastructure`` Github repository in a web browser.
#. Click on the "Actions" tab.
#. On the far right, in the "Filter workflow runs" box, put in ``branch:main``
#. In the center of the screen under "workflow run results", click the topmost entry.
#. In the center of the screen, you should now see a box labeled ``pulumi-prod / pulumi``, click that.
#. In the center of the screen, you should now see a variety of grey steps on a black background. Click on "Pulumi Up" to expand it.
#. Scroll all the way to the bottom of the page. Under ``--outputs:--``, you should be able to see the name of the computer you just created (e.g. ``cambridge--cytation-5``), you can also search for it in the upper right box.
#. You should see something with the format of ``location--computer-name-activation-script`` (e.g. ``cambridge--cytation-5-activation-script``). Next to it, you should see some text starting with ``$dir`` and ending with ``'AmazonSSMAgent';``. Copy that chunk of text.
#. On the lab computer, open the start menu and type "Windows Powershell" and open it (you do not need to open it in Administrator mode).
#. Paste the text you copied into the Powershell window and press Enter.
#. During the installation process, you will likely be prompted to allow the installation of the Amazon Web Services SSM Agent---press yes (this single step requires administrator permissions).
