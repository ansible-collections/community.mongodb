#### first run
0. start minikube
1. make sure cert-manager is installed
2. `openssl genrsa -out ca.key 8192`
3. `openssl req -x509 -new -nodes -key ca.key -sha256 -subj "/CN=mongodb-cluster-ca.local" -days 36500 -reqexts v3_req -extensions v3_ca -out ca.crt`
4. `kubectl create secret tls mongodb-cluster-ca-key-pair --key=ca.key --cert=ca.crt`
5. `kubectl apply -f ca-issuer.yaml`
6. `make install`
7. `kubectl create ns ansible-operator-system`
7. `make deploy IMG=maaeps/test-mongodb-operator:latest`
8. `kubectl apply -f config/samples/mongodb_v1alpha1_mongodb.yaml && sleep 10 && kubectl -n ansible-operator-system logs deployment.apps/ansible-operator-controller-manager -c manager --follow`

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