db.getSiblingDB("admin").runCommand({
    createUser: "admin",
    pwd: "{{admin_password}}",
    roles: [{role: "root", db: "admin"}]
})