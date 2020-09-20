FROM quay.io/operator-framework/ansible-operator:v1.0.0

USER 0
COPY mongodb-org-4.2.repo /etc/yum.repos.d/mongodb-org-4.2.repo
RUN yum -y update \
    && yum install -y python36-devel python3-pip python3-setuptools mongodb-org-shell

RUN rm /etc/yum.repos.d/mongodb-org-4.2.repo

RUN pip3 install pymongo

RUN yum remove -y python36-devel \
    && yum clean all \
    && rm -rf /var/cache/yum

USER ${USER_UID}

COPY requirements.yml ${HOME}/requirements.yml
RUN ansible-galaxy collection install -r ${HOME}/requirements.yml \
 && chmod -R ug+rwx ${HOME}/.ansible

RUN mkdir -p ${HOME}/.ansible/collections/ansible_collections/community/mongodb  && curl -L https://github.com/ansible-collections/community.mongodb/archive/auth_mechanisms.tar.gz | tar --strip-components=1 -C ${HOME}/.ansible/collections/ansible_collections/community/mongodb -xz

COPY watches.yaml ${HOME}/watches.yaml
COPY roles/ ${HOME}/roles/
COPY playbooks/ ${HOME}/playbooks/