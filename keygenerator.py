import rsa

public, private = rsa.newkeys(1024)

with open("default-public.pem","wb") as f:
    f.write(public.save_pkcs1("PEM"))


with open("default-private.pem","wb") as f:
    f.write(private.save_pkcs1("PEM"))

print("Successfully created and written new key pair")