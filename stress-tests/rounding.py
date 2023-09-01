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

def round_decrypted_vector(vector, decimal_places):
    rounded_vector = np.round(vector, decimals=decimal_places)
    return rounded_vector

def rounding_stress_test(num_iterations, decimal_places):
    for i in range(num_iterations):
        print(f"Rounding Stress Test - Iteration {i+1}/{num_iterations}")

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

        context = ts.context_from(read_data_from_s3("s3Bucket", "secret.txt"))
        enc_v1_proto = read_data_from_s3("s3Bucket", f"enc_v1_{i}.txt")
        enc_v1 = ts.lazy_ckks_vector_from(enc_v1_proto)
        enc_v1.link_context(context)
        dec_v1 = enc_v1.decrypt()[0]
        rounded_dec_v1 = round_decrypted_vector(dec_v1, decimal_places)
        rounded_dec_v1_proto = rounded_dec_v1.tobytes()
        write_data_to_s3("s3Bucket", f"rounded_dec_v1_{i}.txt", rounded_dec_v1_proto)
        del context, enc_v1, dec_v1, rounded_dec_v1

        context = ts.context_from(read_data_from_s3("s3Bucket", "secret.txt"))
        rounded_dec_v1_proto = read_data_from_s3("s3Bucket", f"rounded_dec_v1_{i}.txt")
        rounded_dec_v1 = np.frombuffer(rounded_dec_v1_proto, dtype=np.float64)

        distance = dst.findEuclideanDistance(img1_embedding, img2_embedding)
        rounded_distance = round(distance, decimal_places)
        if np.array_equal(rounded_dec_v1, rounded_distance):
            print("Rounding integrity maintained")
        else:
            print("Rounding integrity compromised")

        print("Original rounded distance:", rounded_distance)
        print("Decrypted rounded distance:", rounded_dec_v1)
        print()

if __name__ == "__main__":
    rounding_stress_test(10, decimal_places=2)