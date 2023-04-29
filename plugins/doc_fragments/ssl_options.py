from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


class ModuleDocFragment(object):
    # Standard documentation
    DOCUMENTATION = r'''
options:
  ssl:
    description:
    - Whether to use an SSL connection when connecting to the database.
    required: no
    type: bool
    default: no
    aliases:
      - tls
  ssl_cert_reqs:
    description:
    - Bypass validation of server certificate.
    required: no
    type: bool
    default: no
    aliases:
      - tlsAllowInvalidCertificates
  ssl_ca_certs:
    description:
      - The ssl_ca_certs option takes a path to a CA file.
    required: no
    type: str
    aliases:
      - tlsCAFile
  ssl_crlfile:
    description:
      - The ssl_crlfile option takes a path to a CRL file.
    required: no
    type: str
  ssl_certfile:
    description:
      - Present a client certificate using the ssl_certfile option.
    required: no
    type: str
    aliases:
      - tlsCertificateKeyFile
  ssl_keyfile:
    description:
      - Private key for the client certificate.
    required: no
    type: str
  ssl_pem_passphrase:
    description:
      - Passphrase to decrypt encrypted private keys.
    required: no
    type: str
    aliases:
      - tlsCertificateKeyFilePassword
  auth_mechanism:
    description:
      - Authentication type.
    required: no
    type: str
    choices:
      - 'SCRAM-SHA-256'
      - 'SCRAM-SHA-1'
      - 'MONGODB-X509'
      - 'GSSAPI'
      - 'PLAIN'
  connection_options:
    description:
      - Additional connection options.
      - Supply as a list of dicts or strings containing key value pairs seperated with '='.
    required: no
    type: list
    elements: raw
'''
