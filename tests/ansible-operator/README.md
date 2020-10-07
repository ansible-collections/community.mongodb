#### first run
0. start minikube - `minikube start`
1. make sure cert-manager is installed - `kubectl apply --validate=false -f https://github.com/jetstack/cert-manager/releases/download/v1.0.1/cert-manager.yaml`
2. `openssl genrsa -out ca.key 8192`
3. `openssl req -x509 -new -nodes -key ca.key -sha256 -subj "/CN=mongodb-cluster-ca.local" -days 36500 -reqexts v3_req -extensions v3_ca -out ca.crt`
4. `kubectl create secret tls mongodb-cluster-ca-key-pair --key=ca.key --cert=ca.crt`
5. `kubectl apply -f ca-issuer.yaml`
6. `make install`
7. `kubectl create ns ansible-operator-system`
7. `make deploy IMG=maaeps/test-mongodb-operator:latest`
8. `kubectl apply -f config/samples/mongodb_v1alpha1_mongodb.yaml && sleep 10 && kubectl -n ansible-operator-system logs deployment.apps/ansible-operator-controller-manager -c manager --follow`
9. Forward 27017 to the pod - `kubectl port-forward mongodb-sample-0 27017:27017`

#### Connect to mongodb:
```shell
kubectl -n ansible-operator-system exec -ti deployment.apps/ansible-operator-controller-manager -c manager -- \
    /usr/bin/mongo mongodb://mongodb-sample.default.svc.cluster.local \
          --tls \
          --tlsCAFile /tmp/mongodb-sample.default/ca.crt \
          --tlsCertificateKeyFile=/tmp/mongodb-sample.default/tls.key \
          --authenticationMechanism MONGODB-X509 \
          --authenticationDatabase '$external'
```

#### make changes:
`make redeploy IMG=username/repository:latest && kubectl apply -f config/samples/mongodb_v1alpha1_mongodb.yaml && sleep 10 && kubectl -n ansible-operator-system logs deployment.apps/ansible-operator-controller-manager -c manager --follow`

#### View MongoDB Logs

`kubectl logs mongodb-sample-0 --follow`

#### Login to the manager container

`kubectl -n ansible-operator-system exec -ti deployment.apps/ansible-operator-controller-manager -c manager bash`

#### Copy the certs to the localhost

```bash
kubectl cp ansible-operator-system/ansible-operator-controller-manager-86bdf8f5db-wpm6f:/tmp/mongodb-sample.default/ca.crt ca.crt -c manager
kubectl cp ansible-operator-system/ansible-operator-controller-manager-86bdf8f5db-wpm6f:/tmp/mongodb-sample.default/tls.key tls.key -c manager
```

#### A bit of python test code

```python
import ssl
from pymongo import MongoClient
client = MongoClient('localhost', authMechanism="MONGODB-X509", ssl=True, ssl_certfile='tls.key', ssl_cert_reqs=ssl.CERT_REQUIRED, ssl_ca_certs='ca.crt', tlsAllowInvalidHostnames=True)
for db in client.list_databases():
  print(db)
```

#### Local module testing

```
ansible localhost -m mongodb_user -a "login_host=localhost login_port=27017 login_database='$external' database='admin' password='secret' ssl=true ssl_ca_certs=/Users/rhyscampbell/Documents/git/mongodb-kub/tests/ansible-operator/ca.crt ssl_certfile=/Users/rhyscampbell/Documents/git/mongodb-kub/tests/ansible-operator/tls.key auth_mechanism=MONGODB-X509 name="test" state=present connection_options='tlsAllowInvalidHostnames=true'"
```
