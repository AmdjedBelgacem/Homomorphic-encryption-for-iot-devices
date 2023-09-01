import boto3
import tenseal as ts
import numpy as np
import base64

aws_access_key = local.ACCESS_KEY
aws_secret_key = local.SECRET_KEY
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)

def write_data_to_s3(bucket, key, data):
    if type(data) == bytes:
        data = base64.b64encode(data)
    s3.put_object(Bucket=bucket, Key=key, Body=data)

def read_data_from_s3(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    data = response['Body'].read()
    return base64.b64decode(data)

def addition_stress_test(num_iterations):
    for i in range(num_iterations):
        print(f"Addition Stress Test - Iteration {i+1}/{num_iterations}")

        embeddings = generate_random_embeddings(2)
        img1_embedding = embeddings[0]
        img2_embedding = embeddings[1]

        context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60])
        context.generate_galois_keys()
        context.global_scale = 2 ** 40
        secret_context = context.serialize(save_secret_key=True)
        write_data("secret.txt", secret_context)
        context.make_context_public()
        public_context = context.serialize()
        write_data("public.txt", public_context)
        del context, secret_context, public_context

        context = ts.context_from(read_data_from_s3("s3Bucket", "public.txt"))
        enc_v1 = ts.ckks_vector(context, img1_embedding)
        enc_v1_proto = enc_v1.serialize()
        write_data_to_s3("s3Bucket", f"enc_v1_{i}.txt", enc_v1_proto)
        del context, enc_v1

        context = ts.context_from(read_data_from_s3("s3Bucket", "public.txt"))
        enc_v2 = ts.ckks_vector(context, img2_embedding)
        enc_v2_proto = enc_v2.serialize()
        write_data_to_s3("s3Bucket", f"enc_v2_{i}.txt", enc_v2_proto)
        del context, enc_v2

        context = ts.context_from(read_data_from_s3("s3Bucket", "secret.txt"))
        enc_v1_proto = read_data_from_s3("s3Bucket", f"enc_v1_{i}.txt")
        enc_v1 = ts.lazy_ckks_vector_from(enc_v1_proto)
        enc_v1.link_context(context)
       
        context = ts.context_from(read_data_from_s3("s3Bucket", "secret.txt"))
        enc_v2_proto = read_data_from_s3("s3Bucket", f"enc_v2_{i}.txt")
        enc_v2 = ts.lazy_ckks_vector_from(enc_v2_proto)
        enc_v2.link_context(context)

        sum_enc = enc_v1 + enc_v2
        sum_dec = sum_enc.decrypt()
       
        distance = dst.findEuclideanDistance(img1_embedding, img2_embedding)
        sum_distance = distance * 2
       
        if np.allclose(sum_dec, sum_distance, atol=1e-5):
            print("Addition integrity maintained")
        else:
            print("Addition integrity compromised")

        print("Original sum distance:", sum_distance)
        print("Decrypted sum distance:", sum_dec)
        print()

if __name__ == "__main__":
    addition_stress_test(10)