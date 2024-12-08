FROM quay.io/operator-framework/ansible-operator:v1.0.0

USER 0
COPY tests/ansible-operator/mongodb-org-8.0.repo /etc/yum.repos.d/mongodb-org-8.0.repo
RUN yum -y update \
    && yum install -y python36-devel python3-pip python3-setuptools mongodb-mongosh

RUN rm /etc/yum.repos.d/mongodb-org-8.0.repo

RUN pip3 install pymongo

RUN yum remove -y python36-devel \
    && yum clean all \
    && rm -rf /var/cache/yum

USER ${USER_UID}

COPY tests/ansible-operator/requirements.yml ${HOME}/requirements.yml
RUN ansible-galaxy collection install -r ${HOME}/requirements.yml \
 && chmod -R ug+rwx ${HOME}/.ansible

RUN mkdir -p ${HOME}/.ansible/collections/ansible_collections/community/mongodb
 # && curl -L https://github.com/ansible-collections/community.mongodb/archive/auth_mechanisms.tar.gz | tar --strip-components=1 -C ${HOME}/.ansible/collections/ansible_collections/community/mongodb -xz

COPY . ${HOME}/.ansible/collections/ansible_collections/community/mongodb/

COPY tests/ansible-operator/watches.yaml ${HOME}/watches.yaml
COPY tests/ansible-operator/roles/ ${HOME}/roles/
COPY tests/ansible-operator/playbooks/ ${HOME}/playbooks/