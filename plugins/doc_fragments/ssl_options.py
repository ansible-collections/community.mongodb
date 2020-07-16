from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

class ModuleDocFragment(object):
    # Standard documentation
    DOCUMENTATION = r'''
    options:
      ssl_ca_certs:
        description:
          - The ssl_ca_certs option takes a path to a CA file.
        required: no
        type: str
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
    '''
