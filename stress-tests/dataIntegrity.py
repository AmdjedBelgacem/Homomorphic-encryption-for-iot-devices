def stress_test_data_integrity(num_iterations):
    aws_access_key = local.ACCESS_KEY
    aws_secret_key = local.SECRET_KEY
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
   
    for i in range(num_iterations):
        print(f"Running stress test iteration {i+1}/{num_iterations}")

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
        dec_v1 = enc_v1.decrypt()[0]

        context = ts.context_from(read_data_from_s3("s3Bucket", "secret.txt"))
        enc_v2_proto = read_data_from_s3("s3Bucket", f"enc_v2_{i}.txt")
        enc_v2 = ts.lazy_ckks_vector_from(enc_v2_proto)
        enc_v2.link_context(context)
        dec_v2 = enc_v2.decrypt()[0]

        euclidean_squared = dec_v1 - dec_v2
        euclidean_squared = euclidean_squared * euclidean_squared

        distance = dst.findEuclideanDistance(img1_embedding, img2_embedding)
        squared_distance = distance * distance
        if abs(squared_distance - euclidean_squared) < 0.00001:
            print("Data integrity maintained")
        else:
            print("Data integrity compromised")

        print("Original squared distance:", squared_distance)
        print("Decrypted squared distance:", euclidean_squared)
        print()

if __name__ == "__main__":
    stress_test_data_integrity(10)