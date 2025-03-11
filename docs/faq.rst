.. _faq:

Frequently Asked Questions
==========================

Is any encryption involved?
    Yes, and it's all handled automatically.
    When data are uploaded, it's over HTTPS, which means it's encrypted in transit using TLS.
    When the data are in the AWS cloud, they are encrypted at-rest using AES-256.

How can activity be audited?
    The agent running on the laboratory PCs creates a log detailing the files uploaded, timestamps, and the checksums. The log is in JSON format to be easily ingestible by SIEM systems.
    For auditing the cloud infrastructure deployment/configuration, Cloud Courier sets up any user-access with least-privilege permissions by default, and the entire history is version-controlled via Git. AWS also has a feature called CloudTrail that can be enabled to log any action performed and by what entity.

Does Cloud Courier require that my company already has a Single Sign-On (SSO) provider?
    No, Cloud Courier can work with or without an SSO provider. If your company does not have an SSO provider, Cloud Courier will set up AWS Identity Center as the default SSO provider.
